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
image = os.environ.get('TEST_IMAGE_PATH') or "/home/infrasim/jenkins/data/ubuntu14.04.4.qcow2"

conf = {}
error_inject_list = [
    'nvme -i dev-nvme-0 -n 1 -s 4 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 5 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 6 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 18 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 25 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 130 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 132 -t 0',
    'nvme -i dev-nvme-0 -n 1 -s 128 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 129 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 130 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 131 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 132 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 133 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 134 -t 2',
    'nvme -i dev-nvme-0 -n 1 -s 135 -t 2'
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
        ssh = helper.prepare_ssh()
        s = UnixSocket(path)
        s.connect()
        s.recv()
        payload_enable_qmp = {
            "execute": "qmp_capabilities"
        }
        s.send(json.dumps(payload_enable_qmp))
        s.recv()
        for cmd_error_inject in error_inject_list:
            payload_error_inject = {
                "execute": "nvme-status-code-error-inject",
                "arguments": {
                    "command-line": cmd_error_inject
                }
            }

            s.send(json.dumps(payload_error_inject))
            s.recv()
            stdin, stdout, stderr = ssh.exec_command('nvme read /dev/nvme0n1 -z 3008 -a 128')
            self.assertNotIn('Success', stdout, "error inject fail")

        payload_error_inject = {
            "execute": "nvme-status-code-error-inject",
            "arguments": {
                "command-line": 'nvmeclear'
            }
        }

        s.send(json.dumps(payload_error_inject))
        s.recv()

        s.close()
        ssh.close()
