from flask_restplus import Resource
from infrasim.monitor.apis import api
from infrasim.workspace import Workspace


ns = api.namespace("admin", "InfraSIM monitor administration")


@ns.route('/')
class default(Resource):
    def get(self):
        return "Hello world to InfraSIM Monitor", 200


@ns.route('/<string:nodename>')
class root(Resource):
    def get(self, nodename):
        """
        Show workspace details on this InfraSIM host
        """
        node_info = Workspace.get_node_info_in_workspace(nodename)
        return node_info, 200
