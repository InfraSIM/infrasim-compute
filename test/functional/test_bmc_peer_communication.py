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
from infrasim import run_command
from test.fixtures import FakeConfig
from infrasim.model import CNode
from infrasim import sshclient
from infrasim import config, helper
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
    topo = Topology(ivn_file)
    topo.create()


def teardown_module():
    global ivn_file
    topo = Topology(ivn_file)
    topo.delete()
    os.unlink(ivn_file)
    os.environ['PATH'] = old_path


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_bmc_communication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global fake_node0
        global fake_node1
        fake_node0 = test_bmc_communication.node_cfg_up('test0', 'node0ns', fixtures.a_boot_image, "dell_r730")
        fake_node1 = test_bmc_communication.node_cfg_up('test1', 'node1ns', fixtures.b_boot_image, "quanta_d51")

    @classmethod
    def tearDownClass(cls):
        global fake_node0
        global fake_node1
        global topo
        test_bmc_communication._stop_node(fake_node0)
        test_bmc_communication._stop_node(fake_node1)

    @staticmethod
    def _stop_node(node_obj):
        node_obj.stop()
        node_obj.terminate_workspace()

    @staticmethod
    def _start_node(node_info, node_name, node_type):
        fake_node_obj = CNode(node_info)
        fake_node_obj.init()
        fake_node_obj.precheck()
        node_dir = os.path.join(config.infrasim_home, node_name)
        emu_dir = os.path.join(node_dir, "data")
        emu_file = os.path.join(emu_dir, node_type + ".emu")
        if node_name == "test0":
            f = open(emu_file, "ab")
            f.write("\n" + add_content0[0] + "\n" + add_content0[1])
            f.close()
        if node_name == "test1":
            f = open(emu_file, "ab")
            f.write("\n" + add_content1[0] + "\n" + add_content1[1])
            f.close()
        fake_node_obj.start()
        return fake_node_obj

    @staticmethod
    def node_cfg_up(node_name, ns_name, boot_image, node_type):
        global add_content0
        global add_content1
        fake_node = None
        fake_node = copy.deepcopy(FakeConfig().get_node_info())
        fake_node['name'] = node_name
        fake_node['type'] = node_type
        fake_node['namespace'] = ns_name
        fake_node['compute']['storage_backend'][0]["drives"][0]["file"] = boot_image
        fake_node["compute"]["networks"][0]["port_forward"] = [{"outside": 8022, "inside": 22, "protocal": "tcp"}]
        fake_node["bmc"] = {}
        fake_node["bmc"]["peer-bmcs"] = [
            {
                "port_ipmb": 9009
            }
        ]

        if node_name == "test0":
            fake_node["bmc"]["address"] = 0x1c
            fake_node["bmc"]["peer-bmcs"][0]["addr"] = 0x1e
            fake_node["bmc"]["peer-bmcs"][0]["host"] = "192.168.188.92"
            fake_node["bmc"]["peer-bmcs"][0]["port_ipmb"] = 9009
        else:
            fake_node["bmc"]["address"] = 0x1e
            fake_node["bmc"]["peer-bmcs"][0]["addr"] = 0x1c
            fake_node["bmc"]["peer-bmcs"][0]["host"] = "192.168.188.91"
            fake_node["bmc"]["peer-bmcs"][0]["port_ipmb"] = 9009

        fake_node_up = test_bmc_communication._start_node(fake_node, node_name, node_type)
        return fake_node_up

    def client_ssh(self, ns_ip):
        ssh = sshclient.SSH(host=ns_ip, username="root", password="root", port=8022)
        ssh.wait_for_host_up()
        return ssh

    def test_peer_bmc_fru(self):
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[0])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[0])
        self.assertIn("PowerEdge R730", result0, "peer_bmc can not Obtain fru")
        self.assertIn("Quanta Computer", result1, "peer_bmc can not Obtain fru")

    def test_peer_bmc_lan(self):
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[1])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[1])
        self.assertIn("MAC Address", result0, "peer_bmc can not Obtain lan")
        self.assertIn("MAC Address", result1, "peer_bmc can not Obtain lan")
        self.assertNotEqual(result0, result1, "peer_bmc can not Obtain lan")

    def test_peer_bmc_sensor(self):
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[2])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[2])
        self.assertNotEqual(result0, result1, "peer_bmc can not Obtain sensor")

    def test_peer_bmc_sel(self):
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result0 = node0_ssh.exec_command(cmd_prefix0[3])
        node0_ssh = self.client_ssh('192.168.188.91')
        status, result1 = node0_ssh.exec_command(cmd_prefix1[3])
        self.assertNotEqual(result0, result1, "peer_bmc can not Obtain sensor")

    @unittest.skip("skip test, don't supoort lan access feature now")
    def test_peer_node_off_on(self):
        os.system(cmd_prefix1[4])
        PS_QEMU = "ps ax | grep qemu"
        qemu_result = run_command(PS_QEMU, True, subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = helper.get_full_qemu_cmd(qemu_result)

        self.assertNotIn("test1", qemu_result, "peer_bmc can not power off")
        """
        test peer bmc on
        """
        os.system(cmd_prefix1[5])
        node1_ssh = self.client_ssh('192.168.188.92')
        status, result = node1_ssh.exec_command('ls')
        assert result

    @unittest.skip("skip test, don't supoort lan access feature now")
    def test_peer_node_cycle(self):
        os.system(cmd_prefix1[6])
        node1_ssh = self.client_ssh('192.168.188.92')
        status, result = node1_ssh.exec_command('ls')
        assert result
