from flask_restplus import Api
from .redfish_1_0_0 import api as redfish_api_1_0_0

api = Api()

api.add_namespace(redfish_api_1_0_0)
