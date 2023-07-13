from typing import Optional

from flask import Flask, jsonify
from flask_restful import Api, Resource, reqparse

from policy import (
    Policy,
    SpendLimit
)

from db import Session
from models import (
    Utxos,
    SpentUtxos,
    AggregateSpends,
    SignedSpends,
    UTXOS_SCHEMA,
    SPENT_UTXOS_SCHEMA,
    AGGREGATE_SPENDS_SCHEMA,
    SIGNED_SPENDS_SCHEMA
)


parser = reqparse.RequestParser()
parser.add_argument('psbt', required=True, type=str, location=['json', 'form'], help='valid psbt to sign')

class SignPsbt(Resource):
    def post(self):
        args = parser.parse_args()
        
        pass

def create_app(debug=False)-> Flask:
    app = Flask(__name__)
    if debug:
            app.app_env = 'development'
        else:
            app.app_env = 'production'

    api = Api(self.app)
    api.add_resource(SignPsbt, '/process-psbt')


def setup_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error_code=400, message="Bad Request"), 400

    @app.errorhandler(404)
    def route_not_found(e):
            return jsonify(
                error_code=404,
                message="No such endpoint",
                endpoints=["/process-psbt"]
                ), 404

    @app.errorhandler(405)
    def wrong_method(e):
        return jsonify({error_code=405, message="Only the POST Method is allowed"}), 405

def main():
    # Create tables
    Session.execute(UTXOS_SCHEMA)
    Session.execute(SPENT_UTXOS_SCHEMA)
    Session.execute(AGGREGATE_SPENDS_SCHEMA)
    Session.execute(SIGNED_SPENDS_SCHEMA)

    # Todo


if __name__ == '__main__':
    main()
