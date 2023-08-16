import os
import re
import time
import math
import argparse
import threading

from typing import Optional
from sqlite3 import OperationalError, IntegrityError, DatabaseError

from flask import Flask, jsonify, request


from .errors import ServerError
from .daemon import daemon
from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .config import Configuration
from .policy import (
    Policy,
    PolicyHandler,
    PolicyException,
    SpendLimit
)

from .models import (
    Utxos,
    SpentUtxos,
    SignedSpends,
    AggregateSpends
)

from .analysis import descriptor_analysis, ResignerPsbt, analyse_psbt_from_base64_str

def setup_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error_code=400, message="Bad Request"), 400

    @app.errorhandler(404)
    def route_not_found(e):
            return jsonify(error_code=404, message="No such endpoint"), 404

    @app.errorhandler(405)
    def wrong_method(e):
        return jsonify(error_code=405, message="Only the POST Method is allowed"), 405
    
    @app.errorhandler(PolicyException)
    def policy_error(e):
        return jsonify(error_code=403, message=str(e)), 403

    @app.errorhandler(ServerError)
    def error_handler(e):
        # Todo: log
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500

    @app.errorhandler(Exception)
    def error_handler(e):
        # Todo: log
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500


def sign_transaction(psbt: str, config: Configuration):
    btcd = config.get("bitcoind")["client"]
    signed_psbt = ""
    try:
        # Todo: also sign spends from change 
        signed_psbt = btcd.walletprocesspsbt(psbt)
    except BitcoindRPCError as e:
        print("signing psbt failed psbt: ", psbt)
        raise ServerError(e)

    # Todo: implement a proper error reporting
    return signed_psbt

def create_route(app):
    @app.route('/process-psbt', methods=['POST'])
    def ProcessPsbt():
        request_timestamp = math.floor(time.time() * 1000000)
        policy_handler = app.config["route_args"]["policy_handler"]
        config = app.config["route_args"]["config"]

        args = request.get_json()
        
        psbt_obj = analyse_psbt_from_base64_str(args["psbt"], config)

        try:
            policy_handler.run({"psbt": psbt_obj})
        except PolicyException as e:
            raise PolicyException(e.message)

        # Todo: check if the psbt was actually signed.
        signed = False
        result = sign_transaction(args["psbt"], config)
        if result["complete"] is not True:
            # Todo: should fail here
            pass

        SignedSpends.insert(
                args["psbt"],
                result["psbt"],
                psbt_obj.amount_sats,
                request_timestamp,
                False
        )

        tx = SignedSpends.get([], {"request_timestamp": request_timestamp})[0]
        for utxo in psbt_obj.utxos:
            SpentUtxos.insert(utxo["txid"], utxo["vout"], tx["id"])

        agg_spends = AggregateSpends.get()[0]
        AggregateSpends.update(
            {
                "unconfirmed_daily_spends": agg_spends["unconfirmed_daily_spends"] + psbt_obj.amount_sats,
                "unconfirmed_weekly_spends": agg_spends["unconfirmed_weekly_spends"] + psbt_obj.amount_sats,
                "unconfirmed_monthly_spends": agg_spends["unconfirmed_monthly_spends"] + psbt_obj.amount_sats
            }
        )

        # Due to bitcoind policies we don't actually know if the psbt was signed. we only know that it didn't throw an error
        return jsonify(psbt=result["psbt"], signed=True)

def create_app(config: Configuration, policy_handler: PolicyHandler, debug=True)-> Flask:
    app = Flask(__name__)
    if debug:
        app.app_env = 'development'
    else:
        app.app_env = 'production'

    app.config["route_args"] = {"config": config, "policy_handler": policy_handler}

    setup_error_handlers(app)
    create_route(app)
    return app

def init_db():
    """Initialise database"""
    Utxos.create()
    SpentUtxos.create()
    SignedSpends.create()
    AggregateSpends.create()

    # Insert the only record in AggregateSpends Table
    if not AggregateSpends.get():
        AggregateSpends.insert()


def local_main(debug: Optional[bool] = False, port: Optional[int] = 7767):
    # Setup args
    parser = argparse.ArgumentParser(description='Signing Service for Miniscript Policies.')
    parser.add_argument('--config_path', type=str, help='configuration path')
   
    config_path =  os.getenv("RESIGNER_CONFIG_PATH") or parser.parse_args().config_path

    if not config_path:
        raise ServerError("Resigner started without configuration path")

    # Intialise Configuration
    config = Configuration(config_path)

    # Initialise bitcoind rpc client
    bitcoind = config.get("bitcoind")
    rpc_url = bitcoind["rpc_url"] if re.search("/wallet" ,bitcoind["rpc_url"]) else\
        f"{bitcoind['rpc_url']}/wallet/{config.get('wallet')['wallet_name']}"
    btd_client = BitcoindRPC(
        rpc_url,
        bitcoind["bitcoind_rpc_user"],
        bitcoind["bitcoind_rpc_password"]
    )

    # Initialize bitcoind rpc client for change wallet
    search = re.search("/wallet" ,bitcoind["rpc_url"])
    rpc_url = f"{bitcoind['rpc_url'][0:(search.span[1]-1)]}/{config.get('wallet')['change_wallet_name']}"\
        if search  else f"{bitcoind['rpc_url']}/wallet/{config.get('wallet')['change_wallet_name']}"

    btd_change_client = BitcoindRPC(
        rpc_url,
        bitcoind["bitcoind_rpc_user"],
        bitcoind["bitcoind_rpc_password"]
    )

    config.set({"client": btd_client}, "bitcoind")
    config.set({"change_client": btd_change_client}, "bitcoind")


    # Analyse Descriptor
    descriptor_analysis(config)

    # Init DB
    init_db()

    # Set db sync status
    config.set({"synced_db_with_onchain_data": False},"resigner_config")

    
    # Setup daemon
    condition = threading.Condition()
    threading.Thread(target=daemon, args=([config, condition]), daemon=True).start()

    print("Syncing db with blockchain. Might take a couple minutes depending on the amount of the unspent utxos")
    
    start_sync_time = time.time()
    def db_is_synced() -> bool:
        print("syncing db with onchain data took : ", time.time() - start_sync_time, "seconds")
        return config.get("resigner_config")["synced_db_with_onchain_data"]

    #Wait on db to sync with the blockchain
    with condition:
        condition.wait_for(db_is_synced)

    # Setup PolicyHandler
    policy_handler = PolicyHandler()
    policy_handler.register_policy(
        [
            SpendLimit(config),
        ]
    )

    app = create_app(config, policy_handler)

    app.run(debug=debug, port=port)    

if __name__ == '__main__':
    local_main()
