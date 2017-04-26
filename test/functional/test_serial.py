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
from infrasim import model
from test import fixtures
import shutil
import subprocess
import time
import re

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


class test_ipmi_sol(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        time.sleep(3)

        # Start sol in a subprocess
        self.fw = open('/tmp/test_sol', 'wb')
        self.p_sol = subprocess.Popen("ipmitool -I lanplus -U admin -P admin "
                                      "-H 127.0.0.1 sol activate",
                                      shell=True,
                                      stdin=subprocess.PIPE,
                                      stdout=self.fw,
                                      stderr=self.fw,
                                      bufsize=1)

    def tearDown(self):
        self.p_sol.stdin.write("~.")
        self.p_sol.kill()
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        os.remove("/tmp/test_sol")
        self.conf = None

    def test_ipmi_sol(self):
        """
        Activate SOL and verify it accepts serial data
        """
        # This method refer to a solution on stackoverflow:
        # http://stackoverflow.com/questions/19880190/interactive-input-output-using-python

        # Send ipmitool in shell within another sub process
        # and make sure it's sent correctly
        p_power = subprocess.Popen("ipmitool -I lanplus -U admin -P admin "
                                   "-H 127.0.0.1 chassis power reset",
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        p_power.communicate()
        p_power_ret = p_power.returncode
        if p_power_ret != 0:
            raise self.fail("Fail to send chassis power reset command")

        # Check if sol session has get something
        time.sleep(10)
        self.fw.close()
        self.fr = open('/tmp/test_sol', 'r')
        sol_out = self.fr.read()
        self.fr.close()

        # SOL will print a hint at first
        # After this hint message, any ASCII char indicates
        # the SOL receives something and it means SOL is alive
        deli = "[SOL Session operational.  Use ~? for help]"
        deli_index = sol_out.find(deli)
        string_left = sol_out[len(deli)+deli_index:]
        p = re.compile(r"\w")

        assert p.search(string_left) is not None
