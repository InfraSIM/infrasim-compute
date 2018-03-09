'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import time
import re
import os
from infrasim import model
from infrasim import run_command
from test import fixtures
from infrasim import config
from infrasim.log import infrasim_logdir


# command prefix for test cases
log_path = os.path.join(infrasim_logdir, 'test/ipmi_sim.log')
ipmi_fru_list = "ipmitool -H 127.0.0.1 -U admin -P admin fru list"
class test_ipmi_sim_full_log(unittest.TestCase):
    def setUp(self):
        self.node_info = {}
        fake_config = fixtures.FakeConfig()
        self.node_info = fake_config.get_node_info()
        self.node_info["bmc"] = {
                    "full_log": True
        }
        node = model.CNode(self.node_info)
        node.init()
        node.precheck()
        node.start()
        # FIXME: sleep is not a good way to wait qemu starts up.
        time.sleep(3)

    def tearDown(self):
        node = model.CNode(self.node_info)
        node.init()
        node.stop()
        node.terminate_workspace()

    def test_full_log(self):
        try:
            status_output = run_command(ipmi_fru_list)[1]
            with open(log_path, "r") as fp:
                lines = fp.readlines()
            assert "Activate session" in str(lines)

        except Exception as e:
            print e
            import traceback
            print traceback.format_exc()
            assert False


class test_ipmi_sim_error_log_only(unittest.TestCase):
    def setUp(self):
        self.node_info = {}
        fake_config = fixtures.FakeConfig()
        self.node_info = fake_config.get_node_info()
        node = model.CNode(self.node_info)
        node.init()
        node.precheck()
        node.start()
        # FIXME: sleep is not a good way to wait qemu starts up.
        time.sleep(3)

    def tearDown(self):
        node = model.CNode(self.node_info)
        node.init()
        node.stop()
        node.terminate_workspace()

    def test_full_log(self):
        try:
            status_output = run_command(ipmi_fru_list)[1]
            with open(log_path, "r") as fp:
                lines = fp.readlines()
            assert "Activate session" not in str(lines)
            assert "Error command" in str(lines)

        except Exception as e:
            print e
            import traceback
            print traceback.format_exc()
            assert False
