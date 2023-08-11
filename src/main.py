import os
import re
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

from .db import Session
from .models import (
    UTXOS_SCHEMA,
    SPENT_UTXOS_SCHEMA,
    AGGREGATE_SPENDS_SCHEMA,
    SIGNED_SPENDS_SCHEMA,
    Utxos,
    SpentUtxos,
    SignedSpends,
    AggregateSpends
)

from .analysis import descriptor_analysis, ResignerPsbt, analyse_psbt_from_base64_str


def setup_error_handlers(app):
    @app.errorhandler(ServerError)
    def error_handler(e):
        # Todo: log
        print(e)
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error_code=400, message="Bad Request"), 400

    @app.errorhandler(404)
    def route_not_found(e):
            return jsonify(
                error_code=404,
                message="No such endpoint",
                # endpoints=["/process-psbt"] probably shouldn't expose this
                ), 404

    @app.errorhandler(405)
    def wrong_method(e):
        return jsonify(error_code=405, message="Only the POST Method is allowed"), 405

async def sign_transaction(psbt: str, config: Configuration):
    btcd = config.get("bitcoind")["client"]
    signed_psbt = ""
    try:
        print("sign psbt: ", psbt)
        signed_psbt = await btcd.walletprocesspsbt(psbt)
    except BitcoindRPCError as e:
        print("signing psbt failed psbt: ", psbt)
        raise ServerError(e)

    return signed_psbt

def create_route(app):
    @app.route('/process-psbt', methods=['POST'])
    async def ProcessPsbt():
        policy_handler = app.config["route_args"]["policy_handler"]
        config = app.config["route_args"]["config"] 
        args = request.get_json()
        psbt_obj = await analyse_psbt_from_base64_str(args["psbt"], config)

        try:
            policy_handler.run({"psbt": psbt_obj})
        except PolicyException as e:
            raise ServerError(e)

        # Todo: check if the psbt was actually signed.
        ret = await sign_transaction(args["psbt"], config)
        if ret["complete"] is not True:
            # Todo: should fail here
            pass

        for utxo in psbt_obj.utxos:
            try:
                coin = Utxos.get([], {"txid": utxo["txid"], "vout": utxo["vout"]})[0]
                SpentUtxos.insert(coin["id"], utxo["txid"], utxo["vout"])
            except OperationalError as e:
                if not app.debug:
                    return jsonify(
                        error_code=500,
                        message="Cannot sign transactions until Utxo set is fully synced"
                    ), 500
            except IntegrityError as e:
                # Todo: 
                pass

        try:
            _id = SpentUtxos.get(["id"], {"txid": utxo["txid"], "vout": utxo["vout"]})["id"]
            SignedSpends.insert(
                args["psbt"],
                ret["psbt"],
                psbt_obj.amount_sats,
                _id,
                time.time(),
                False
            )
        except OperationalError as e:
            print("Database not fully synced.", e)
        except DatabaseError as e:
            print("Database not fully synced.", e)


        agg_spends = AggregateSpends.get()[0]
        print("agg_spends:", agg_spends)
        AggregateSpends.update(
            {
                "unconfirmed_daily_spends": agg_spends["unconfirmed_daily_spends"] + psbt_obj.amount_sats,
                "unconfirmed_weekly_spends": agg_spends["unconfirmed_weekly_spends"] + psbt_obj.amount_sats,
                "unconfirmed_monthly_spends": agg_spends["unconfirmed_monthly_spends"] + psbt_obj.amount_sats
            }
        )

        agg_spends = AggregateSpends.get()[0]
        print("agg_spends:", agg_spends)

        return jsonify(psbt=ret["psbt"], signed=True)

def create_app(config: Configuration, policy_handler: PolicyHandler, debug=False)-> Flask:
    app = Flask(__name__)
    if debug:
        app.app_env = 'development'
    else:
        app.app_env = 'production'

    app.config["route_args"] = {"config": config, "policy_handler": policy_handler}

    setup_error_handlers(app)
    return app

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
    btcd = BitcoindRPC(
        rpc_url,
        bitcoind["bitcoind_rpc_user"],
        bitcoind["bitcoind_rpc_password"]
    )

    config.set({"client": btcd}, "bitcoind")

    # Analyse Descriptor
    descriptor_analysis(config)

    # Create tables
    try:    
        Session.execute(UTXOS_SCHEMA)
        Session.execute(SPENT_UTXOS_SCHEMA)
        Session.execute(AGGREGATE_SPENDS_SCHEMA)
        Session.execute(SIGNED_SPENDS_SCHEMA)
    except OperationalError as e:
        if not e.__repr__() == "OperationalError('table utxos already exists')":
            raise ServerError(e)
 
    # Insert the only record in AggregateSpends Table
    if not AggregateSpends.get():
        AggregateSpends.insert()

    # Setup daemon
    threading.Thread(target=daemon, args=([config]), daemon=True).start()


    # Setup PolicyHandler
    policy_handler = PolicyHandler()
    policy_handler.register_policy(
        [
            SpendLimit(config),
        ]
    )

    app = create_app(config, policy_handler)
    create_route(app)

    app.run(debug=debug, port=port)    

if __name__ == '__main__':
    local_main()
