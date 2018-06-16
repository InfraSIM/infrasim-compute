"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import json
from infrasim import model
from infrasim import helper
from infrasim import sshclient
from test import fixtures
from infrasim.helper import UnixSocket

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)

conf = {}
error_inject_list = [
    [4, 0, 'Data Transfer'],
    [5, 0, 'Power Loss'],
    [6, 0, 'Internal'],
    [18, 0, 'Invalid Use of Controller Memory Buffer'],
    [25, 0, 'Keep Alive Timeout Expired'],
    [130, 0, 'Namespace Not Ready'],
    [132, 0, 'Format In Progress'],
    [128, 2, 'Write Fault'],
    [129, 2, 'Unrecovered Read '],
    [130, 2, 'End-to-end Guard Check'],
    [131, 2, 'End-to-end Application Tag Check'],
    [132, 2, 'End-to-end Reference Tag Check'],
    [133, 2, 'Compare Failure'],
    [134, 2, 'Access Denied'],
    [135, 2, 'Deallocated or Unwritten Logical Block']
]


def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path


class test_error_inject(unittest.TestCase):

    @staticmethod
    def start_node():
        global conf
        global path
        nvme_config = fixtures.NvmeConfig()
        conf = nvme_config.get_node_info()
        node = model.CNode(conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)
        path = os.path.join(node.workspace.get_workspace(), ".monitor")

    @staticmethod
    def stop_node():
        global conf
        global node
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        conf = {}

    @classmethod
    def setUpClass(cls):
        cls.start_node()

    @classmethod
    def tearDownClass(cls):
        if conf:
            cls.stop_node()

    def test_nvmeerror_inject(self):
        ssh = sshclient.SSH(host="127.0.0.1", username="root", password="root", port=2222)
        ssh.wait_for_host_up()
        s = UnixSocket(path)
        s.connect()
        s.recv()
        payload_enable_qmp = {
            "execute": "qmp_capabilities"
        }
        s.send(json.dumps(payload_enable_qmp))
        s.recv()

        payload_error_inject = {
            "execute": "nvme-status-code-error-inject",
            "arguments": {
                "count": 65536,
                "opcode": "rw",
                "id": "dev-nvme-0",
                "nsid": 1,
                "status_field": {
                    "dnr": True,
                    "more": True
                }
            }
        }
        payload_nvmeclear = {
            'execute': 'nvme-status-code-error-inject',
            'arguments': {
                'count': 0,
                'opcode': 'rw',
                'id': 'dev-nvme-0',
                'nsid': 0,
                'status_field': {
                    'sc': 0,
                    'sct': 0,
                    'dnr': True,
                    'more': True
                }
            }
        }

        for cmd_error_inject in error_inject_list:
            payload_error_inject['arguments']['status_field']['sc'] = cmd_error_inject[0]
            payload_error_inject['arguments']['status_field']['sct'] = cmd_error_inject[1]
            s.send(json.dumps(payload_error_inject))
            s.recv()
            status, output = ssh.exec_command("nvme read /dev/nvme0n1 -z 3008 -a 128")
            self.assertNotIn("Success", output, "error of %s inject faile" % cmd_error_inject[2])

            s.send(json.dumps(payload_nvmeclear))
            s.recv()
            status, output = ssh.exec_command("nvme read /dev/nvme0n1 -z 3008 -a 128")
            self.assertIn("Success", output, "clear error faile")
        s.close()
