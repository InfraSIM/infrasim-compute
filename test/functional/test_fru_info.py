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


def start_node():
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

    conf["compute"]["smbios"] = {
        "type1": {
              "sku_number": "sssdsf",
              "sn": "a1111"
        },
        "type2": {
              "location": "SPA",
              "sn": "a222"
        },
        "type3": {
              "sn": "a3333"
        },
        "type4": {
              "cores": 4,
              "sn": "a4444"
        },
        "type17": [
            {
               "locator": "B1",
               "part_number": "p11716",
               "size": 8,
               "sn": "a1717"
            }
        ]
    }
    conf["bmc"] = {}
    conf["bmc"]["fru0"] = {
        "board": {
             "name": "test1",
             "pn": "p222",
             "sn": "s222"
        }
    }
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

    def test_type1_value(self):
        lines = run_cmd("sudo dmidecode -t1")
        self.assertIn(conf["compute"]["smbios"]["type1"]["sku_number"], lines, "type1 sku_number error")

    def test_type2_value(self):
        lines = run_cmd("sudo dmidecode -t2")
        self.assertIn(conf["compute"]["smbios"]["type2"]["location"], lines, "type2 location error")
        self.assertIn(conf["compute"]["smbios"]["type2"]["sn"], lines, "type2 sn error")

    def test_type3_value(self):
        lines = run_cmd("sudo dmidecode -t3")
        self.assertIn(conf["compute"]["smbios"]["type3"]["sn"], lines, "type3 sn  error")

    def test_type4_value(self):
        lines = run_cmd("sudo dmidecode -t4")
        self.assertIn(conf["compute"]["smbios"]["type4"]["sn"], lines, "type4 sn  error")

    def test_type17_value(self):
        lines = run_cmd("sudo dmidecode -t17")
        self.assertIn(conf["compute"]["smbios"]["type17"][0]["sn"], lines, "type17 sn error")
        self.assertIn(conf["compute"]["smbios"]["type17"][0]["part_number"], lines, "type17 pn error")

    def test_bmc_fru_value(self):
        lines = run_cmd("sudo ipmitool fru list 0")
        self.assertIn(conf["bmc"]["fru0"]["board"]["name"], lines, "bmc fru  error")
        self.assertIn(conf["bmc"]["fru0"]["board"]["pn"], lines, "bmc fru  error")
        self.assertIn(conf["bmc"]["fru0"]["board"]["sn"], lines, "bmc fru  error")
