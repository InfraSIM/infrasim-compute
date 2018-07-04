"""
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
"""
import copy
import unittest
import os
import subprocess
import tempfile
import yaml
import sys
from test.fixtures import FakeConfig
from infrasim.model import CNode
from infrasim import sshclient
from infrasim import config
from test import fixtures

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
conf = {}
ivn_file = None
fake_node0 = None
fake_node1 = None
global add_content0
global add_content1
cmd_prefix0 = [
    'sudo ipmitool fru print 0',
    'sudo ipmitool lan print',
    'sudo ipmitool sensor list',
    'sudo ipmitool sel list'
]

cmd_prefix1 = [
    'sudo ipmitool -t 0x1e fru print 0',
    'sudo ipmitool -t 0x1e lan print',
    'sudo ipmitool -t 0x1e sensor list',
    'sudo ipmitool -t 0x1e sel list',
    'ipmitool -t 0x1e -U admin -P admin -H 192.168.188.91 chassis bootdev pxe',
    'ipmitool -t 0x1e -U admin -P admin -H 192.168.188.91 power off',
    'ipmitool -t 0x1e -U admin -P admin -H 192.168.188.91 power on',
    'ipmitool -t 0x1e -U admin -P admin -H 192.168.188.91 power reset'
]

add_content0 = [
    "mc_add 0x1e 1 no-device-sdrs 1 0 0 159 0 0 dynsens",
    "mc_enable 0x1e"
]
add_content1 = [
    "mc_add 0x1c 1 no-device-sdrs 1 0 0 159 0 0 dynsens",
    "mc_enable 0x1c"
]

try:
    from ivn.core import Topology
except ImportError as e:
    path_ivn = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "ivn")
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
    topo = Topology(ivn_file)
    topo.delete()
    os.unlink(ivn_file)
    os.environ['PATH'] = old_path


class test_bmc_communication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        global fake_node0
        global fake_node1
        if fake_node0:
            test_bmc_communication._stop_node(fake_node0)
        if fake_node1:
            test_bmc_communication._stop_node(fake_node1)

    @staticmethod
    def _stop_node(node_obj):
        node_obj.stop()
        node_obj.terminate_workspace()

    def _start_node(self, node_info):
        fake_node_obj = CNode(node_info)
        fake_node_obj.init()
        fake_node_obj.precheck()
        fake_node_obj.start()
        return fake_node_obj

    def node_cfg_up(self, node_name, ns_name, boot_image, node_type):
        global add_content0
        global add_content1
        global emu_file_for_del0
        global emu_file_for_del1
        fake_node = None
        fake_node = copy.deepcopy(FakeConfig().get_node_info())

        emu_dir = os.path.join(config.infrasim_data, node_type)
        emu_file = os.path.join(emu_dir, node_type + ".emu")
        if ns_name == "node0ns":
            for i in add_content0:
                emu_file_for_del0 = emu_file
                os.system("echo {} >> {}".format(i, emu_file))
        if ns_name == "node1ns":
            for i in add_content1:
                emu_file_for_del1 = emu_file
                os.system("echo {} >> {}".format(i, emu_file))

        fake_node['name'] = node_name
        fake_node['type'] = node_type
        fake_node['namespace'] = ns_name
        fake_node['compute']['storage_backend'][0]["drives"][0]["file"] = boot_image
        fake_node["compute"]["networks"][0]["port_forward"] = [{"outside": 8022, "inside": 22, "protocal": "tcp"}]
        fake_node["bmc"] = {}
        fake_node["bmc"]["peer-bmcs"] = [
            {
                "interface": "lanplus",
                "user": "admin",
                "password": "admin"
            }
        ]

        if node_name == "test0":
            fake_node["bmc"]["peer-bmcs"][0]["addr"] = 0x1e
            fake_node["bmc"]["peer-bmcs"][0]["host"] = "192.168.188.92"
        else:
            fake_node["bmc"]["peer-bmcs"][0]["addr"] = 0x1c
            fake_node["bmc"]["peer-bmcs"][0]["host"] = "192.168.188.91"

        fake_node_up = self._start_node(fake_node)
        return fake_node_up

    def client_ssh(self, ns_ip):
        ssh = sshclient.SSH(host=ns_ip, username="root", password="root", port=8022)
        ssh.wait_for_host_up()
        return ssh

    def test_peer_bmc_communication(self):
        global cmd_prefix0
        global cmd_prefix1
        global ivn_file
        global fake_node0
        global fake_node1
        global emu_file
        global emu_file_for_del0
        global emu_file_for_del1
        topo = Topology(ivn_file)
        topo.create()
        fake_node0 = self.node_cfg_up('test0', 'node0ns', fixtures.a_boot_image, "dell_r730")
        fake_node1 = self.node_cfg_up('test1', 'node1ns', fixtures.b_boot_image, "quanta_d51")

        """
        Test peer_bmc fru print
        """
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[0])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[0])
        self.assertIn("PowerEdge R730", result0, "peer_bmc can not Obtain fru")
        self.assertIn("Quanta Computer", result1, "peer_bmc can not Obtain fru")

        """
        Test peer_bmc lan print
        """
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[1])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[1])
        self.assertIn("MAC Address", result0, "peer_bmc can not Obtain lan")
        self.assertIn("MAC Address", result1, "peer_bmc can not Obtain lan")
        self.assertNotEqual(result0, result1, "peer_bmc can not Obtain lan")

        """
        Test peer_bmc sensor list
        """
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[2])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[2])
        self.assertNotEqual(result0, result1, "peer_bmc can not Obtain sensor")

        """
        Test peer_bmc sel list
        """
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[3])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[3])
        self.assertNotEqual(result0, result1, "peer_bmc can not Obtain sensor")

        """
        Test peer_bmc off, on and cycle
        """
        node1_ssh = self.client_ssh('192.168.188.92')
        os.system(cmd_prefix1[4])
        os.system(cmd_prefix1[5])
        result_net = subprocess.check_output(["netstat", "-an4p"])
        self.assertNotIn("192.168.188.92", result_net, "peer_bmc can not power off")

        os.system(cmd_prefix1[6])
        node1_ssh = self.client_ssh('192.168.188.92')
        status, result = node1_ssh.exec_command('ls')
        assert result

        os.system(cmd_prefix1[4])
        os.system(cmd_prefix1[7])
        node1_ssh = self.client_ssh('192.168.188.92')
        status, result = node1_ssh.exec_command('ls')
        assert result

        os.system("sed -i '$d' {}".format(emu_file_for_del0))
        os.system("sed -i '$d' {}".format(emu_file_for_del0))
        os.system("sed -i '$d' {}".format(emu_file_for_del1))
        os.system("sed -i '$d' {}".format(emu_file_for_del1))

        test_bmc_communication._stop_node(fake_node0)
        test_bmc_communication._stop_node(fake_node1)
        fake_node0 = None
        fake_node1 = None
        topo.delete()
