"""
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import re
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
        result1 = subprocess.check_output(['ovs-vsctl', 'list-br'])
        self.assertIn("br-int", result1, "vswitch is missing")
        result2 = subprocess.check_output(['ovs-vsctl', 'list-ports','br-int'])
        self.assertIn("vint0", result2, "ports is missing")
        self.assertIn("vint1", result2, "ports is missing")
        result = subprocess.check_output(["ip", "netns", "list"])
        reobj = re.search(r'node1ns(\s?\(id:\s?\d+\))?', result)
        assert reobj
        reobj = re.search(r'node0ns(\s?\(id:\s?\d+\))?', result)
        assert reobj

        topo.delete()
        result = subprocess.check_output(["ip", "netns", "list"])
        self.assertNotIn("node1ns", result, "delete node1ns failed")
        self.assertNotIn("node0ns", result, "delete node0ns failed")
        result1 = subprocess.check_output(['ovs-vsctl', 'list-br'])
        self.assertNotIn("br-int", result1, "delete vswitch success")
