from typing import Optional

from flask import Flask
from flask_restful import Api, Resource, reqparse

parser = reqparse.RequestParser()
parser.add_argument('psbt', required=True, type=str, location=['json', 'form'], help='valid psbt to sign')


class SignPsbt(Resource):
    def post(post):
        # args = parser.parse_args()
        # Todo: handle psbt
        pass


class SigningService:
    ''' Signing service API class'''

    def __init__(self, port: Optional[int] = 5000, debug: Optional[bool] = False):
        self.app = Flask(__name__)
        if debug:
            self.app.app_env = 'development'
        else:
            self.app.app_env = 'production'

        self._api = Api(self.app)
        self._api.add_resource(SignPsbt, '/process-psbt')

    def run(self):
        self.app.run(debug=False)
