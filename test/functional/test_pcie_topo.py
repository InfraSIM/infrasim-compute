'''
*********************************************************
Copyright @ 2017 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import time
from infrasim import model
from infrasim import helper
from infrasim import InfraSimError
import paramiko
from test import fixtures
from infrasim.helper import UnixSocket
import json


"""
Test inquiry/mode sense data injection of scsi drive
"""
conf = {}
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    global conf
    if conf:
        stop_node()
    os.environ["PATH"] = old_path


def port_forward(node):

    # Port forward from guest 22 to host 2222
    path = os.path.join(node.workspace.get_workspace(), ".monitor")
    s = UnixSocket(path)
    s.connect()
    s.recv()

    payload_enable_qmp = {
        "execute": "qmp_capabilities"
    }

    s.send(json.dumps(payload_enable_qmp))
    s.recv()

    payload_port_forward = {
        "execute": "human-monitor-command",
        "arguments": {
            "command-line": "hostfwd_add ::2222-:22"
        }
    }
    s.send(json.dumps(payload_port_forward))
    s.recv()

    s.close()


def start_node(node_type):
    """
    create pcie_topo
    """
    global conf
    global tmp_conf_file
    global ssh
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["boot"] = {
        "boot_order": "c"
        }
    conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [
                {
                    "size": 8,
                    "file": fixtures.image
                }
            ]}, {
            "bus": "downstream4",
            "type": "nvme",
            "cmb_size": 256,
            "drives": [{"size": 8}]
        }]

    conf["compute"]["networks"] = [{
        "bus": "downstream1",
        "device": "e1000",
        "mac": "52:54:be:b9:77:dd",
        "network_mode": "nat",
        "network_name": "dummy0"
    }]
    conf["compute"]["pcie_topology"] = {
      "root_port": [
        {
          "addr": "7.0",
          "bus": "pcie.0",
          "chassis": 1,
          "device": "ioh3420",
          "id": "root_port1",
          "pri_bus": 0,
          "sec_bus": 40,
          "slot": 2
        },
        {
          "addr": "8.0",
          "bus": "pcie.0",
          "chassis": 1,
          "device": "ioh3420",
          "id": "root_port2",
          "pri_bus": 0,
          "sec_bus": 60,
          "slot": 3
        }
      ],
      "switch": [
        {
          "downstream": [
            {
              "addr": "2.0",
              "bus": "upstream1",
              "chassis": 1,
              "device": "xio3130-downstream",
              "id": "downstream1",
              "slot": 190,
              "pri_bus": 41,
              "sec_bus": 42
            },
            {
              "addr": "3.0",
              "bus": "upstream1",
              "chassis": 1,
              "device": "xio3130-downstream",
              "id": "downstream2",
              "slot": 160,
              "pri_bus": 41,
              "sec_bus": 43
            }
          ],
          "upstream": [
            {
              "bus": "root_port1",
              "device": "x3130-upstream",
              "id": "upstream1"
            }
          ]
        },
        {
          "downstream": [
            {
              "addr": "2.0",
              "bus": "upstream2",
              "chassis": 1,
              "device": "xio3130-downstream",
              "id": "downstream3",
              "slot": 193,
              "pri_bus": 61,
              "sec_bus": 62
            },
            {
              "addr": "3.0",
              "bus": "upstream2",
              "chassis": 1,
              "device": "xio3130-downstream",
              "id": "downstream4",
              "slot": 164,
              "pri_bus": 61,
              "sec_bus": 63
            }
          ],
          "upstream": [
            {
              "bus": "root_port2",
              "device": "x3130-upstream",
              "id": "upstream2"
            }
          ]
        }
      ]
    }

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()
    time.sleep(3)
    port_forward(node)
    time.sleep(3)

    # wait until system is ready for ssh.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="root", password="root", timeout=120)
    ssh.close()


def stop_node():
    global conf
    global tmp_conf_file
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}


def run_cmd(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="root", password="root", timeout=120)

    stdin, stdout, stderr = ssh.exec_command(cmd)
    while not stdout.channel.exit_status_ready():
        pass
    lines = stdout.channel.recv(4096)
    ssh.close()
    return lines


class test_pcie_topo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node(node_type="quanta_d51")

    @classmethod
    def tearDownClass(cls):
        stop_node()

    @staticmethod
    def get_cfg_list(keywd):
        pcie_topo_list = run_cmd("lspci").split('\n')
        bus_list = [x.split(" ")[0].split(":")[0] for x in pcie_topo_list if keywd in x]
        rp_cfg_list = conf["compute"]["pcie_topology"]["root_port"]
        downstream_cfg_list = []
        for sw in conf["compute"]["pcie_topology"]["switch"]:
            for ds in sw["downstream"]:
                downstream_cfg_list.append(ds)

        return bus_list, downstream_cfg_list + rp_cfg_list

    def test_pcie_bridge(self):
        # check pcie topology
        pcie_topo_list = run_cmd("lspci")
        rootport_num = pcie_topo_list.count('Root Port')
        upstream_num = pcie_topo_list.count('Upstream')
        downstream_num = pcie_topo_list.count('Downstream')
        if rootport_num != len(conf["compute"]["pcie_topology"]["root_port"]):
            self.assertIn("Root port number doesn't match!")
        switch_list = conf["compute"]["pcie_topology"]["switch"]
        upstream_in_switch = 0
        downstream_in_switch = 0
        for sl in switch_list:
            upstream_in_switch += len(sl["upstream"])
            downstream_in_switch += len(sl["downstream"])
        assert upstream_num == upstream_in_switch
        assert downstream_num == downstream_in_switch

    def test_pcie_upstream_bus(self):
        # check pcie number
        pcie_topo_list = run_cmd("lspci").split('\n')
        upstream_bus_list = [x.split(" ")[0].split(":")[0] for x in pcie_topo_list if 'Upstream' in x]
        upstream_bus_list.sort()
        sec_bus_list = []
        for root in conf["compute"]["pcie_topology"]["root_port"]:
            if 'sec_bus' in root:
                sec_bus_list.append(hex(root['sec_bus'])[2:])
        sec_bus_list.sort()
        assert sec_bus_list == upstream_bus_list

    def test_nic_bdf(self):
        # check nic bdf match config
        nic_bus_list, cfg_list = self.get_cfg_list('Ethernet')
        nic_cfg_list = conf["compute"]["networks"]
        nic_cfg_bus_list = []
        for rp in cfg_list:
            for nic in nic_cfg_list:
                if nic["bus"] == rp["id"]:
                    nic_cfg_bus_list.append(hex(rp["sec_bus"])[2:])
        assert set(nic_bus_list) == set(nic_cfg_bus_list)

    def test_nvme_bdf(self):
        # check nvme bdf match config
        nvme_bus_list, cfg_list = self.get_cfg_list('8606')
        nvme_cfg_list = [x for x in conf["compute"]["storage_backend"] if x['type'] == 'nvme']
        nvme_cfg_bus_list = []
        for rp in cfg_list:
            for nvme in nvme_cfg_list:
                if nvme["bus"] == rp["id"]:
                    nvme_cfg_bus_list.append(hex(rp["sec_bus"])[2:])
        assert set(nvme_bus_list) == set(nvme_cfg_bus_list)
