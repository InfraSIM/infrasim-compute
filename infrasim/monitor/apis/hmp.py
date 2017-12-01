from flask_restplus import Resource, abort, fields
from infrasim.monitor.apis import api
from infrasim.monitor.qemu_api import QemuMonitor


ns = api.namespace("hmp", "HMP operation")

cmd_line = api.model("command-line",{
    "command-line": fields.String(default = "info chardev")
})

hmp_cmd = api.model("hmp command format",{
    "execute": fields.String(default = "human-monitor-command"),
    "arguments": fields.Nested(cmd_line)
})

@ns.route('/<string:nodename>')
class root(Resource):
    def get(self, nodename):
        return "Hello world HMP", 200

    @api.expect(hmp_cmd)
    def post(self, nodename):
        qm = QemuMonitor(nodename)
        qm.connect()
        cmd = api.payload
        qm.send(cmd)
        recv = qm.recv().decode('string_escape')

        return recv, 200
