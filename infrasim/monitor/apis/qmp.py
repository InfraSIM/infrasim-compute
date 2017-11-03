from flask_restplus import Resource, abort
from infrasim.monitor.apis import api


ns = api.namespace("qmp", "QMP operation")


@ns.route('/')
class root(Resource):
    def get(self):
        return "Hello world QMP", 200
