'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import unittest
import os
from infrasim import model
from infrasim import config
from infrasim import run_command
from test import fixtures


old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    os.environ["PATH"] = old_path


class test_control_by_lib(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()
        cls.node_root = os.path.join(config.infrasim_home, cls.conf["name"])

    @classmethod
    def tearDownClass(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None

    def test_lib_start_stop(self):
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check node runtime pid file exist
        node_name = self.conf["name"]
        node_socat = os.path.join(self.node_root, ".{}-socat.pid".format(node_name))
        node_ipmi = os.path.join(self.node_root, ".{}-bmc.pid".format(node_name))
        node_qemu = os.path.join(self.node_root, ".{}-node.pid".format(node_name))
        self.assertTrue(os.path.exists(node_socat))
        self.assertTrue(os.path.exists(node_ipmi))
        self.assertTrue(os.path.exists(node_qemu))

        # Check node runtime process exist
        with open(node_socat, 'r') as fp:
            pid_socat = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_socat)))
        with open(node_ipmi, 'r') as fp:
            pid_ipmi = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_ipmi)))
        with open(node_qemu, 'r') as fp:
            pid_qemu = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_qemu)))

        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()

        # Check node runtime pid file don't exist
        self.assertFalse(os.path.exists(node_socat))
        self.assertFalse(os.path.exists(node_ipmi))
        self.assertFalse(os.path.exists(node_qemu))

        # Check node runtime process don't exist any more
        self.assertFalse(os.path.exists("/proc/{}".format(pid_socat)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_ipmi)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_qemu)))


class test_control_by_cli(unittest.TestCase):

    node_name = "default"
    node_workspace = os.path.join(config.infrasim_home, node_name)

    def tearDown(self):
        os.system("infrasim node destroy {}".format(self.node_name))
        os.system("rm -rf {}".format(self.node_workspace))
        os.system("pkill socat")
        os.system("pkill ipmi")
        os.system("pkill qemu")

    def test_normal_start_stop(self):

        run_command("infrasim node start")

        # Check node runtime pid file exist
        node_socat = os.path.join(self.node_workspace, ".{}-socat.pid".format(self.node_name))
        node_ipmi = os.path.join(self.node_workspace, ".{}-bmc.pid".format(self.node_name))
        node_qemu = os.path.join(self.node_workspace, ".{}-node.pid".format(self.node_name))
        self.assertTrue(os.path.exists(node_socat))
        self.assertTrue(os.path.exists(node_ipmi))
        self.assertTrue(os.path.exists(node_qemu))

        # Check node runtime process exist
        with open(node_socat, 'r') as fp:
            pid_socat = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_socat)))
        with open(node_ipmi, 'r') as fp:
            pid_ipmi = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_ipmi)))
        with open(node_qemu, 'r') as fp:
            pid_qemu = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_qemu)))

        run_command("infrasim node stop")

        # Check node runtime pid file don't exist
        self.assertFalse(os.path.exists(node_socat))
        self.assertFalse(os.path.exists(node_ipmi))
        self.assertFalse(os.path.exists(node_qemu))

        # Check node runtime process don't exist any more
        self.assertFalse(os.path.exists("/proc/{}".format(pid_socat)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_ipmi)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_qemu)))

        run_command("infrasim node destroy")

        # Check node runtime pid file don't exist
        self.assertFalse(os.path.exists(node_socat))
        self.assertFalse(os.path.exists(node_ipmi))
        self.assertFalse(os.path.exists(node_qemu))

        # Check node runtime process don't exist any more
        self.assertFalse(os.path.exists("/proc/{}".format(pid_socat)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_ipmi)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_qemu)))
