from flask_restplus import Resource, abort
from infrasim.monitor.apis import api


ns = api.namespace("hmp", "HMP operation")


@ns.route('/')
class root(Resource):
    def get(self):
        return "Hello world HMP", 200
