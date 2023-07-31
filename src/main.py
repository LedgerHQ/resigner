import argparse
from typing import Optional
from sqlite3 import OperationalError

from flask import Flask, jsonify
from flask_restful import Api, Resource, reqparse

from .errors import ServerError
from .bitcoind_rpc_client import BitcoindRPC, BitcoindRPCError
from .config import Configuration
from .policy import (
    Policy,
    SpendLimit
)

from .db import Session
from .models import (
    Utxos,
    SpentUtxos,
    AggregateSpends,
    SignedSpends,
    UTXOS_SCHEMA,
    SPENT_UTXOS_SCHEMA,
    AGGREGATE_SPENDS_SCHEMA,
    SIGNED_SPENDS_SCHEMA
)

from .analysis import Psbt

parser = reqparse.RequestParser()
parser.add_argument('psbt', required=True, type=str, location=['json', 'form'], help='valid psbt to sign')

def setup_error_handlers(app):
    @app.errorhandler(Exception)
    def error_handler(e):
        # Todo: log
        print(e)
        return jsonify(error_code=500, message="Internal Server Error"), 500

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

class ResignerResource(Resource):
    def __init__(self, *args, config: Optional[Configuration] = None, **kwargs):
        if config is None:
            raise RuntimeError("Argument 'config' must not be None")
        super().__init__(*args, **kwargs)
        self._config = config

    @property
    def config(self):
        return self._config


class SignPsbt(ResignerResource):
    def post(self):
        args = parser.parse_args()
        psbt_obj = Psbt(args["psbt"], self.config)
        
        return args

def create_app(config: Configuration, debug=False)-> Flask:
    app = Flask(__name__)
    if debug:
        app.app_env = 'development'
    else:
        app.app_env = 'production'

    api = Api(app)
    api.add_resource(SignPsbt, '/process-psbt', resource_class_kwargs={"config": config})

    setup_error_handlers(app)
    return app

def local_main():
    # Setup args
    parser = argparse.ArgumentParser(description='Signing Service for Miniscript Policies.')
    parser.add_argument('--config_path', type=str, help='configuration path')
   
    args = parser.parse_args()
    if not args.config_path:
        raise ServerError("Resigner started without configuration path")

    # Intialise Configuration
    config = Configuration(args.config_path)

    # Initialise bitcoind rpc client
    bitcoind = config.get("bitcoind")
    btcd = BitcoindRPC(
        bitcoind["rpc_url"],
        bitcoind["bitcoind_rpc_user"],
        bitcoind["bitcoind_rpc_password"]
    )

    # Create tables
    try:    
        Session.execute(UTXOS_SCHEMA)
        Session.execute(SPENT_UTXOS_SCHEMA)
        Session.execute(AGGREGATE_SPENDS_SCHEMA)
        Session.execute(SIGNED_SPENDS_SCHEMA)
    except OperationalError as e:
        if not e.__repr__() == "OperationalError('table utxos already exists')":
            raise ServerError(e)
 
    app = create_app(config)

    app.run(debug=True, port=7767)    

if __name__ == '__main__':
    local_main()
