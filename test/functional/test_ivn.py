"""
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import subprocess
import tempfile
import yaml
import sys

from test import fixtures

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
image = os.environ.get('TEST_IMAGE_PATH') or "/home/infrasim/jenkins/data/ubuntu14.04.4.qcow2"
conf = {}
ivn_file = None

try:
    from ivn.core import Topology
except ImportError as e:
    path_ivn = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "ivn")
    print path_ivn
    sys.path.append(path_ivn)
    from ivn.core import Topology


def saved_config_file():
    ivn_cfg = fixtures.IvnConfig()
    fi = tempfile.NamedTemporaryFile(delete=False)
    yaml.safe_dump(ivn_cfg.get_ivn_info(), fi, default_flow_style=False)
    fi.close()
    return fi.name


def setup_module():
    global ivn_file
    os.environ['PATH'] = new_path
    ivn_file = saved_config_file()


def teardown_module():
    global ivn_file
    os.unlink(ivn_file)
    os.environ['PATH'] = old_path


class test_ivn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_ns_create_delete(self):
        global ivn_file
        topo = Topology(ivn_file)
        topo.create()
        result = subprocess.check_output(["ip", "netns", "list"])
        self.assertIn("node1ns (id:", result, "node1ns is missing")
        self.assertIn("node0ns (id:", result, "node0ns is missing")

        topo.delete()
        result = subprocess.check_output(["ip", "netns", "list"])
        self.assertNotIn("node1ns (id:", result, "delete node1ns failed")
        self.assertNotIn("node0ns (id:", result, "delete node0ns failed")
