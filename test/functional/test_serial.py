'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import yaml
from infrasim import socat
from infrasim import config
from test import fixtures
import shutil

"""
Test serial functions:
    - socat can create serial device
    - qemu connect to it
    - SOL (serial over lan) work as expected
"""


class test_serial(unittest.TestCase):
    TMP_CONF_FILE = "/tmp/test.yml"
    @classmethod
    def setUpClass(cls):
        socat.stop_socat()

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    def tearDown(self):
        socat.stop_socat(conf_file=self.TMP_CONF_FILE)

        if os.path.exists(self.TMP_CONF_FILE):
            os.unlink(self.TMP_CONF_FILE)

        workspace = os.path.join(config.infrasim_home, self.conf['name'])
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace)

        self.conf = None

    def test_socat_create_serial_device_file(self):
        target_device = "/tmp/pty_serial"
        if os.path.isfile(target_device) or os.path.islink(target_device):
            os.unlink(target_device)

        # Start socat and device shall be created
        self.conf["sol_device"] = target_device
        with open(self.TMP_CONF_FILE, "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        socat.start_socat(conf_file=self.TMP_CONF_FILE)

        if os.path.islink(target_device):
            assert True
        else:
            assert False

        # Remove socat and device shall be collected
        socat.stop_socat()
        if os.path.isfile(target_device) or os.path.islink(target_device):
            assert False
        else:
            assert True
