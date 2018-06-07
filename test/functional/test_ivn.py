"""
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
"""
import copy
import unittest
import re
import os
import subprocess
import tempfile
import yaml
import sys
import shutil
from infrasim import run_command
from test.fixtures import FakeConfig
from infrasim.model import CNode
from infrasim import sshclient
from test import fixtures

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
a_boot_image = os.environ.get('TEST_IMAGE_PATH') or "/home/infrasim/jenkins/data/ubuntu16.04_a.qcow2"
b_boot_image = "/home/infrasim/jenkins/data/ubuntu16.04_b.qcow2"
conf = {}
ivn_file = None
fake_node1 = None
fake_node2 = None

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
    if os.path.exists(a_boot_image) is False:
        raise Exception("Not found image {}".format(a_boot_image))
    if os.path.exists(b_boot_image) is False:
        shutil.copy(a_boot_image, b_boot_image)
    ivn_file = saved_config_file()


def teardown_module():
    global ivn_file
    topo = Topology(ivn_file)
    topo.delete()
    os.unlink(ivn_file)
    os.environ['PATH'] = old_path


class test_ivn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        global fake_node1
        global fake_node2
        if fake_node1:
            test_ivn._stop_node(fake_node1)
        if fake_node2:
            test_ivn._stop_node(fake_node2)

    @staticmethod
    def _stop_node(node_obj):
        node_obj.stop()
        node_obj.terminate_workspace()

    def _verify_node_in_netns(self, node_obj, netns):
        for task in node_obj.get_task_list():
            pid = task.get_task_pid()
            print pid
            _, output = run_command("ip netns identify {}".format(pid))
            self.assertIn(netns, output, "node is not in namespace {}".format(netns))

    def _start_node(self, node_info):
        fake_node_obj = CNode(node_info)
        fake_node_obj.init()
        fake_node_obj.precheck()
        fake_node_obj.start()
        return fake_node_obj

    def node_config(self, node_name, ns_name, boot_image):
        fake_node = None
        fake_node = copy.deepcopy(FakeConfig().get_node_info())
        fake_node['name'] = node_name
        fake_node['namespace'] = ns_name
        fake_node['compute']['storage_backend'][0]["drives"][0]["file"] = boot_image
        fake_node["compute"]["networks"][0]["port_forward"] = [{"outside": 8022, "inside": 22, "protocal": "tcp"}]
        fake_node_up = self._start_node(fake_node)
        return fake_node_up

    def client_ssh(self, ns_ip):
        ssh = sshclient.SSH(host=ns_ip, username="root", password="root", port=8022)
        ssh.wait_for_host_up()
        status, output = ssh.exec_command("ls")
        return output

    def test_ns_create_delete(self):
        global ivn_file
        global fake_node1
        global fake_node2
        topo = Topology(ivn_file)
        topo.create()
        result1 = subprocess.check_output(['ovs-vsctl', 'list-br'])
        self.assertIn("br-int", result1, "vswitch is missing")
        result2 = subprocess.check_output(['ovs-vsctl', 'list-ports', 'br-int'])
        self.assertIn("vint0", result2, "ports is missing")
        self.assertIn("vint1", result2, "ports is missing")
        result = subprocess.check_output(["ip", "netns", "list"])
        reobj = re.search(r'node1ns(\s?\(id:\s?\d+\))?', result)
        assert reobj
        reobj = re.search(r'node0ns(\s?\(id:\s?\d+\))?', result)
        assert reobj
        fake_node1 = self.node_config('test0', 'node0ns', a_boot_image)
        fake_node2 = self.node_config('test1', 'node1ns', b_boot_image)
        self._verify_node_in_netns(fake_node1, "node0ns")
        output_ssh = self.client_ssh('192.168.188.91')
        self.assertNotEqual('', output_ssh, 'connection fail')
        self._verify_node_in_netns(fake_node2, "node1ns")
        output_ssh = self.client_ssh('192.168.188.92')
        self.assertNotEqual('', output_ssh, 'connection fail')
        test_ivn._stop_node(fake_node1)
        test_ivn._stop_node(fake_node2)
        fake_node1 = None
        fake_node2 = None
        topo.delete()
        result = subprocess.check_output(["ip", "netns", "list"])
        self.assertNotIn("node1ns", result, "delete node1ns failed")
        self.assertNotIn("node0ns", result, "delete node0ns failed")
        result1 = subprocess.check_output(['ovs-vsctl', 'list-br'])
        self.assertNotIn("br-int", result1, "delete vswitch success")
