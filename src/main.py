import os
import re
import time
import math
import logging
import argparse
import threading

from typing import Optional
from sqlite3 import OperationalError, IntegrityError, DatabaseError

from flask import Flask, jsonify, request, send_from_directory, abort


from .errors import ServerError, UtxoError, UnsafePSBTError, DBError
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

from .analysis import ResignerPsbt, analyse_psbt_from_base64_str


def setup_logging(name="resigner"):  
    #logging.getLogger("werkzeug").disabled = True
    logging.getLogger("httpx").disabled = True
    
    log_format = "%(levelname)s:%(asctime)s.%(msecs)03d:%(name)s: %(message)s"

    logging.basicConfig(level=logging.INFO, format=log_format, datefmt='%H:%M:%S')
    logger = logging.getLogger(name)

    return logger

def setup_error_handlers(app):
    config = app.config["route_args"]["config"]
    logger = config.get("logger")

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error_code=400, message=e.description['message'] or "Bad Request"), 400

    @app.errorhandler(404)
    def route_not_found(e):
            return jsonify(error_code=404, message="No such endpoint"), 404

    @app.errorhandler(405)
    def wrong_method(e):
        if request.path.startswith('/process-psbt'):
            # we return a json saying so
            return jsonify(error_code=405, message="Only the POST Method is allowed"), 405
        else:
            return jsonify(message="Method Not Allowed"), 405
    
    @app.errorhandler(UnsafePSBTError)
    def psbt_error(e):
        return jsonify(error_code=403, message=e.message), 403

    @app.errorhandler(UtxoError)
    def utxo_error(e):
        return jsonify(error_code=403, message=e.message, details={"txid": e.txid, "vout": e.vout}), 403

    @app.errorhandler(PolicyException)
    def policy_error(e):
        return jsonify(error_code=403, message=e.message), 403

    @app.errorhandler(DatabaseError)
    @app.errorhandler(DBError)
    def dberror_handler(e):
        logger.error(f"A Database Error: {e} occured while handling request from IP: {request.environ.get('REMOTE_ADDR', request.remote_addr)}")
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500

    @app.errorhandler(ServerError)
    def bitcoind_error_handler(BitcoindRPCError):
        logger.error(f"An unhandled Exception {e} occured in bitcoind rpc while handling request from IP: {request.environ.get('REMOTE_ADDR', request.remote_addr)}")
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500

    @app.errorhandler(ServerError)
    def error_handler(e):
        logger.error(f"An Internal Server Error {e} occured while handling request from IP: {request.environ.get('REMOTE_ADDR', request.remote_addr)}")
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500

    @app.errorhandler(Exception)
    def error_handler(e):
        logger.error(f"Unhandled Exception: {e} occured while handling request from IP: {request.environ.get('REMOTE_ADDR', request.remote_addr)}")
        return jsonify(error_code=500, message=f"Internal Server Error: {e}"), 500


def sign_transaction(psbt: str, config: Configuration):
    logger = config.get("logger")
    btcd = config.get("bitcoind")["client"]
    signed_psbt = ""
    try:
        logger.info("signing psbt: %s", psbt)
        signed_psbt = btcd.walletprocesspsbt(psbt)
    except BitcoindRPCError as e:
        raise ServerError(e)

    logger.info("Processed PSBT: %s...%s without errors", psbt[:9], psbt[-10:])
    # Todo: implement a proper error reporting
    return signed_psbt

def create_route(app):
    @app.route('/swagger')
    def swagger_ui():
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'swagger'), 'index.html')

    @app.route('/swagger/<path:path>')
    def serve_static(path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'swagger'), path)

    @app.route('/process-psbt', methods=['POST'])
    def ProcessPsbt():
        request_timestamp = math.floor(time.time() * 1000000)
        policy_handler = app.config["route_args"]["policy_handler"]
        config = app.config["route_args"]["config"]
        logger = config.get("logger")

        args = request.get_json()

        if not args["psbt"]:
            abort(400, {'message': 'psbt not supplied in request'}) 
        
        psbt_obj = analyse_psbt_from_base64_str(args["psbt"], config)

        try:
            policy_handler.run({"psbt": psbt_obj})
        except PolicyException as e:
            raise PolicyException(e.message, e.policy)

        # Todo: check if the psbt was actually signed.
        signed = False
        logger.info("Signing PSBT: %s...%s", args["psbt"][0:9], args["psbt"][-10:])
        result = sign_transaction(args["psbt"], config)
        if result["complete"] is not True:
            logger.info("Signed PSBT: %s...%s not complete", result[0:9], result[-10:])
            # Todo: should fail here
            pass

        SignedSpends.insert(
                psbt_obj.txid,
                args["psbt"],
                result["psbt"],
                psbt_obj.amount_sats,
                request_timestamp,
                False
        )

        for utxo in psbt_obj.utxos:
            SpentUtxos.insert(utxo["txid"], utxo["vout"], psbt_obj.txid)

        logger.info("Updating aggregate spends, amount: %d", psbt_obj.amount_sats)
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
    btd_client = BitcoindRPC(
        bitcoind['bitcoind_wallet_rpc_url'],
        bitcoind["bitcoind_rpc_user"],
        bitcoind["bitcoind_rpc_password"]
    )

    config.set({"client": btd_client}, "bitcoind")
    
    # Logging
    logger = setup_logging()
    config.set({"logger": logger})

    # Init DB
    init_db()

    # Set db sync status
    config.set({"synced_db_with_onchain_data": False},"resigner_config")

    
    # Setup daemon
    condition = threading.Condition()
    threading.Thread(target=daemon, args=([config, condition]), daemon=True).start()

    logger.info("Syncing db with blockchain. Might take a couple minutes depending on the amount of the utxos")
    
    start_sync_time = time.time()
    def db_is_synced() -> bool:
        logger.info(f"syncing db with onchain data took : {time.time() - start_sync_time} seconds")
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
