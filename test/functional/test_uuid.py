'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
from test import fixtures
from infrasim import model
from infrasim import helper


conf = None
OLD_PATH = os.environ.get("PATH")
NEW_PATH = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), OLD_PATH)
ssh = None


def setup_module():
    os.environ["PATH"] = NEW_PATH


def teardown_module():
    if conf:
        stop_node()
    os.environ["PATH"] = OLD_PATH


def start_node():
    """
    create two drive for comparasion.
    First drive has additional page, second doesn't
    """
    global conf
    global ssh

    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["networks"][0]["port_forward"] = [
        {
            "protocal": "tcp",
            "inside": 22,
            "outside": 2222
        }
    ]
    conf["compute"]["boot"] = {
        "boot_order": "c"
    }
    conf["compute"]["uuid"] = "9cef4921-fc70-493f-8674-a01801384881"
    conf["compute"]["cpu"] = {
        "type": "Haswell",
        "quantities": 4
    }

    conf["compute"]["memory"] = {
        "size": 4096
    }

    conf["compute"]["storage_backend"] = [
        {
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [
                {
                    "size": 10,
                    "file": fixtures.image
                }
            ]
        }
    ]

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()
    node.wait_node_up()

    ssh = helper.prepare_ssh()


def stop_node():
    global conf
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = None
    helper.ssh_close(ssh)


def run_cmd(cmd):
    return helper.ssh_exec(ssh, cmd)


class test_uuid(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_uuid_value(self):
        lines = run_cmd("sudo dmidecode -t1")
        self.assertIn(conf["compute"]["uuid"].upper(), lines, "uuid error")
