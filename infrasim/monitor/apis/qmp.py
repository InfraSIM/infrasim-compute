from flask_restplus import Resource, fields
from infrasim.monitor.apis import api
from infrasim.monitor.qemu_api import QemuMonitor

ns = api.namespace("qmp", "QMP operation")

cmd_line = api.model("command-line", {
    "command-line": fields.String(default="info chardev")
})

qmp_cmd = api.model("qmp command format", {
    "execute": fields.String(default="human-monitor-command"),
    "arguments": fields.Nested(cmd_line)
})


@ns.route('/<string:nodename>')
class root(Resource):
    def get(self):
        return "Hello world QMP", 200

    @api.expect(qmp_cmd)
    def post(self, nodename):
        qm = QemuMonitor(nodename)
        qm.connect()
        cmd = api.payload
        qm.send(cmd)
        recv = qm.recv().decode('string_escape')

        return recv, 200
