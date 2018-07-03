'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import re
import copy
import paramiko
from infrasim import model
from infrasim import helper
from infrasim import cloud_img
from test import fixtures
from test.fixtures import CloudNetworkConfig
import shutil

conf = None
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None
vmd_bar2_size_GB = 8
boot_image = None
key_iso = None
mac_addr = "52:54:be:b9:77:dd"
cloudimg_folder = "cloudimgs"


def setup_module():
    global boot_image
    global key_iso
    os.environ["PATH"] = new_path
    if os.path.isdir(cloudimg_folder):
        shutil.rmtree(cloudimg_folder, ignore_errors=True)
    if os.path.isfile(cloudimg_folder):
        os.remove(cloudimg_folder)

    os.mkdir(cloudimg_folder)
    boot_image = cloud_img.gen_qemuimg(fixtures.cloud_img_ubuntu_18_04, "mytest0.img")
    newnetwork0 = copy.deepcopy(CloudNetworkConfig().get_network_info())
    newnetwork0["config"][0]["mac_address"] = mac_addr
    newnetwork0["config"] = [newnetwork0["config"][0]]
    key_iso = cloud_img.geniso("my-seed0.iso", "305c9cc1-2f5a-4e76-b28e-ed8313fa283e", newnetwork0)


def teardown_module():
    global boot_image
    stop_node()
    shutil.rmtree(cloudimg_folder, ignore_errors=True)
    os.environ["PATH"] = old_path


def start_node():
    """
    create pcie_topo
    """
    global conf
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["boot"] = {
        "boot_order": "c"
    }
    conf["compute"]['cdrom'] = {'file': key_iso}
    conf["compute"]["storage_backend"] = [
        {
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [
                {
                    "size": 8,
                    "file": boot_image
                }]
        },
        {
            "bus": "downstream1",
            "type": "nvme",
            "cmb_size": 256
        }
    ]

    conf["compute"]["networks"] = [{
        "device": "e1000",
        "mac": mac_addr,
        "network_mode": "nat",
        "port_forward": [
            {
                "protocal": "tcp",
                "inside": 22,
                "outside": 2222
            }
        ]
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
            }
        ],
        "vmd": [
            {
                "addr": "5.5",
                "bus": "pcie.0",
                "device": "vmd",
                "id": "vmd_0",
                "bar2_size": vmd_bar2_size_GB * 1024
            }
        ],
        "switch": [
            {
                "upstream": [
                    {
                        "bus": "vmd_0",
                        "device": "x3130-upstream",
                        "id": "upstream0"
                    }
                ],
                "downstream": [
                    {
                        "bus": "upstream0",
                        "id": "downstream1",
                        "addr": "2.0",
                        "chassis": 1,
                        "device": "xio3130-downstream",
                        "slot": 195,
                        "pri_bus": 1,
                        "sec_bus": 2
                    },
                    {
                        "id": "downstream2",
                        "bus": "upstream0",
                        "addr": "3.0",
                        "chassis": 1,
                        "device": "xio3130-downstream",
                        "slot": 166,
                        "pri_bus": 1,
                        "sec_bus": 3
                    }
                ]
            }
        ]
    }

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()
    node.wait_node_up()


def stop_node():
    global conf
    if conf:
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
    conf = None


def run_cmd(cmd):
    global ssh
    if ssh is None:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("filename.log")

    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="ubuntu", password="password", timeout=120)

    _, stdout, _ = ssh.exec_command(cmd)
    while not stdout.channel.exit_status_ready():
        pass
    lines = stdout.channel.recv(4096)
    ssh.close()
    return lines


class test_pcie_topo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_check_vmd_existence(self):
        # check existence of vmd device
        vmd_info = run_cmd("lspci -s 0000:00:05.5 -vv")

        self.assertIn("Kernel driver in use: vmd", vmd_info, "VMD driver is not loaded")
        self.assertIn("Kernel modules: vmd", vmd_info, "VMD kernel modules is not loaded")

        pattern0 = "Region 0: Memory at [0-9a-f]* \(64-bit, prefetchable\) \[size=128M\]"
        pattern2 = "Region 2: Memory at [0-9a-f]* \(32-bit, non-prefetchable\) \[size=64M\]"
        pattern4 = "Region 4: Memory at [0-9a-f]* \(64-bit, prefetchable\) \[size={}G\]".format(vmd_bar2_size_GB)

        self.assertIsNotNone(re.search(pattern0, vmd_info), "CfgBar config is wrong.\n ret={}".format(vmd_info))
        self.assertIsNotNone(re.search(pattern2, vmd_info), "MemBar1 config is wrong.\n ret={}".format(vmd_info))
        self.assertIsNotNone(re.search(pattern4, vmd_info), "MemBar2 config is wrong.\n ret={}".format(vmd_info))

    def test_check_nvme_ready(self):
        # check nvme is ready for access
        nvme_ret = run_cmd("sudo dd of=/dev/nvme0n1 if=/dev/zero count=100 2>&1")
        self.assertIn("51200 bytes (51 kB, 50 KiB) copied", nvme_ret, "write nvme failed.\n ret={}".format(nvme_ret))

        nvme_ret = run_cmd("sudo dd if=/dev/nvme0n1 of=/dev/null count=100 2>&1")
        self.assertIn("51200 bytes (51 kB, 50 KiB) copied", nvme_ret, "read nvme failed.\n ret={}".format(nvme_ret))

    def test_vmd_domain(self):
        pci_topo_info = run_cmd("lspci")
        self.assertIn("10000:00:00.0 PCI bridge:", pci_topo_info,
                      "Upstream port of switch is not found.\n ret={}".format(pci_topo_info))
        self.assertIn("10000:01:02.0 PCI bridge:", pci_topo_info,
                      "Downstream1 port of switch is not found.\n ret={}".format(pci_topo_info))
        self.assertIn("10000:01:03.0 PCI bridge:", pci_topo_info,
                      "Downstream2 port of switch is not found.\n ret={}".format(pci_topo_info))
        self.assertIn("10000:02:00.0 Non-Volatile memory controller:", pci_topo_info,
                      "Nvme is not found.\n ret={}".format(pci_topo_info))
