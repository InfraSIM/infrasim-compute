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
from test import fixtures
from infrasim.helper import UnixSocket

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)

conf = {}
ssh = None
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
        global ssh
        nvme_config = fixtures.NvmeConfig()
        conf = nvme_config.get_node_info()
        node = model.CNode(conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)
        path = os.path.join(node.workspace.get_workspace(), ".monitor")
        ssh = helper.prepare_ssh("127.0.0.1")

    @staticmethod
    def stop_node():
        global conf
        global node
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        conf = {}
        helper.ssh_close(ssh)

    @classmethod
    def setUpClass(cls):
        cls.start_node()

    @classmethod
    def tearDownClass(cls):
        if conf:
            cls.stop_node()

    def get_nvme_dev(self, dev_sn):
        # find correct dev id by sn
        nvme_list = helper.ssh_exec(ssh, "nvme list -o json")
        nvme_object = json.loads(nvme_list)
        for nvme_dev in nvme_object["Devices"]:
            if nvme_dev["SerialNumber"] == dev_sn:
                return nvme_dev["DevicePath"]
        return None

    def test_nvmeerror_inject(self):
        self.assertIsNotNone(ssh, "Can't connect node by ssh")
        # "dev-nvme-0" is the first NVME dev.
        dev_sn = conf["compute"]["storage_backend"][1]["serial"]
        dev = self.get_nvme_dev(dev_sn)
        self.assertIsNotNone(dev, "Can't found nvme device for sn {}".format(dev_sn))

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
        # Redirect stderr to stdout since 'Success' is printed to stderr sometimes"
        cmd = "nvme read {} -z 3008 -a 128 2>&1".format(dev)

        for cmd_error_inject in error_inject_list:
            payload_error_inject['arguments']['status_field']['sc'] = cmd_error_inject[0]
            payload_error_inject['arguments']['status_field']['sct'] = cmd_error_inject[1]
            s.send(json.dumps(payload_error_inject))
            s.recv()
            output = helper.ssh_exec(ssh, cmd)
            self.assertNotIn("Success", output, "error of %s inject failed" % cmd_error_inject[2])
            s.send(json.dumps(payload_nvmeclear))
            s.recv()
            output = helper.ssh_exec(ssh, cmd)
            self.assertIn("Success", output, "clear error failed")

        s.close()
