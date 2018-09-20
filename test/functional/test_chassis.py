'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import shutil
import subprocess
import unittest
import sys
import tempfile
from test import fixtures
import yaml
import paramiko
import json
from infrasim import helper
from infrasim import model
from infrasim.workspace import ChassisWorkspace

try:
    from ivn.core import Topology
except ImportError as e:
    path_ivn = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "ivn")
    sys.path.append(path_ivn)
    from ivn.core import Topology


old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None
conf = {}
chassis = None
nodes_ip = ["192.168.188.91", "192.168.188.92"]
ivn_cfg_file = None
data_file = {
    "nvme": {
        "slot_17": {
            "vpd": "02 08 01 f8 11 30 30 30 30 30 30 30 30 ff ff ff ff ff ff 00 00 \
                        00 00 00 00 46 6c 61 73 68 74 65 63 20 4e 56 2d 30 32 30 30 38 \
                        20 38 47 42 20 32 2e 35 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                        00 00 07 04 00 00 0a 00 00 19 00 00 4d 00 a0 00 51 00 a5 00 00 \
                        00 f8 11 01 00 ce 80 08 08 30 30 30 30 30 30 30 30 30 30 30 30 \
                        30 30 30 30 30 30 30 30 00 76 00 a8 02 ff ff ff ff ff ff ff ff \
                        ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff \
                        20 38 47 42 20 32 2e 35 00 00 00 00 00 00 00 00 00 00 00 00 00 \
                        02 08 01 f8 11 30 30 30 30 30 30 30 30 30 30 00 00 00 00 00 00 \
                        ff 38 47 42 20 32 2e 35 ff",
            "health_data": "30 1f 21 00 01 00 02 03"
        }
    }
}


def setup_module():
    global ivn_cfg_file
    os.environ["PATH"] = new_path
    if os.path.exists(fixtures.a_boot_image) is False:
        raise Exception("Not found image {}".format(fixtures.a_boot_image))
    if os.path.exists(fixtures.b_boot_image) is False:
        shutil.copy(fixtures.a_boot_image, fixtures.b_boot_image)
    with open("/tmp/trace_items", "w") as fo:
        fo.write("comm_log\n")
        fo.write("comm_failed\n")
    ivn_cfg_file = saved_config_file()
    # check the existence of required namespace.
    cmd = ["ip", "netns", "list"]
    result = subprocess.check_output(cmd)
    if "node1ns " not in result or "node0ns " not in result:
        topo = Topology(ivn_cfg_file)
        topo.create()


def teardown_module():
    global conf
    global ivn_cfg_file
    if conf:
        stop_chassis()
    os.environ["PATH"] = old_path

    topo = Topology(ivn_cfg_file)
    topo.delete()
    os.unlink(ivn_cfg_file)


def saved_config_file():
    ivn_cfg = fixtures.IvnConfig()
    fi = tempfile.NamedTemporaryFile(delete=False)
    yaml.safe_dump(ivn_cfg.get_ivn_info(), fi, default_flow_style=False)
    fi.close()
    return fi.name


def start_chassis():
    """

    """
    global conf
    global ssh
    global chassis
    conf = fixtures.ChassisConfig().get_chassis_info()
    conf["data"]["pn"] = "What_ever_SN"
    conf["data"]["sn"] = "What_ever_SN"
    conf["data"]["psu1_pn"] = "A380-B737-C909"

    node0_log = "/tmp/qemu_node0.log"
    node1_log = "/tmp/qemu_node1.log"
    compute_0 = conf["nodes"][0]["compute"]
    compute_0["storage_backend"][0]["drives"][0]["file"] = fixtures.a_boot_image
    compute_0["extra_option"] = "-D {} -trace events=/tmp/trace_items".format(node0_log)
    compute_0["ntb"] = {"addr": 'a.0',
                        "bus": "pcie.0",
                        "bar1_exp": 15,
                        "bar2_exp": 15,
                        "id": "ntb0",
                        "peer_id": "ntb1"}

    compute_1 = conf["nodes"][1]["compute"]
    compute_1["storage_backend"][0]["drives"][0]["file"] = fixtures.b_boot_image
    compute_1["extra_option"] = "-D {} -trace events=/tmp/trace_items".format(node1_log)
    compute_1["ntb"] = {"addr": 'a.0',
                        "bus": "pcie.0",
                        "bar1_exp": 15,
                        "bar2_exp": 15,
                        "id": "ntb1",
                        "peer_id": "ntb0"}

    if os.path.exists(node0_log):
        os.remove(node0_log)
    if os.path.exists(node1_log):
        os.remove(node1_log)

    chassis = model.CChassis(conf["name"], conf)
    chassis.precheck()
    chassis.init()

    data_file_dir = os.path.join(ChassisWorkspace(conf).get_workspace_data(), "oem_data.json")
    with open(data_file_dir, "w") as f:
        json.dump(data_file, f)
    chassis.start()

    ssh = helper.prepare_ssh("192.168.188.92", 8022)


def stop_chassis():
    global conf
    global tmp_conf_file
    global chassis
    if chassis:
        chassis.destroy()
    conf = {}


def run_cmd(cmd, ip, port=8022):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, ip,
                    port=port, username="root", password="root", timeout=120)

    stdin, stdout, stderr = ssh.exec_command(cmd)
    while not stdout.channel.exit_status_ready():
        pass
    lines = stdout.channel.recv(4096)
    ssh.close()
    return lines


class test_chassis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_chassis()

    @classmethod
    def tearDownClass(cls):
        stop_chassis()

    def test_shared_memory(self):

        with open("/tmp/qemu_node0.log") as fi:
            rst = fi.read()
        self.assertIn("in [commu_internal_check], chassis/psu1_pn={}".format(conf["data"]["psu1_pn"]), rst,
                      "Can't get information from shared memory!")
        self.assertIn("in [commu_internal_check], chassis/sn={}".format(conf["data"]["sn"]), rst,
                      "Can't get information from shared memory!")

        with open("/tmp/qemu_node1.log") as fi:
            rst = fi.read()
        self.assertIn("in [commu_internal_check], chassis/psu1_pn={}".format(conf["data"]["psu1_pn"]), rst,
                      "Can't get information from shared memory!")
        self.assertIn("in [commu_internal_check], chassis/sn={}".format(conf["data"]["sn"]), rst,
                      "Can't get information from shared memory!")

    def test_fru_pn_sn(self):
        for ip in nodes_ip:
            cmd = ["ipmitool", "-I", "lanplus", "-U", "admin", "-P", "admin", "-H", ip, "fru", "print", "0"]
            result = subprocess.check_output(cmd)
            self.assertIn(conf["data"]["pn"], result, "Failed to get pn from node {}".format(ip))
            self.assertIn(conf["data"]["sn"], result, "Failed to get sn from node {}".format(ip))

    def test_smbios_sn(self):
        for ip in nodes_ip:
            result = run_cmd("dmidecode -t chassis", ip, 8022)
            self.assertIn("Serial Number: {}".format(conf["data"]["sn"]),
                          result, "Chassis SN is not correct in {}".format(ip))

    def test_nvme_share_feature(self):
        read_temperatue = ["nvme", "get-feature", "/dev/nvme0n1", "-f", "4", "-s", "0"]
        set_temperatue = ["nvme", "set-feature", "/dev/nvme0n1", "-f", "4", "-v", "0xbef"]
        n0_1 = run_cmd(' '.join(read_temperatue), nodes_ip[0])
        n1_1 = run_cmd(' '.join(read_temperatue), nodes_ip[1])

        run_cmd(' '.join(set_temperatue), nodes_ip[0])

        n0_2 = run_cmd(' '.join(read_temperatue), nodes_ip[0])
        n1_2 = run_cmd(' '.join(read_temperatue), nodes_ip[1])

        self.assertEqual(n0_1, n1_1, "Orignal value mismatch.")
        self.assertEqual(n0_2, n1_2, "New value mismatch.")
        self.assertNotEqual(n0_1, n0_2, "Failed to change value.")

    def test_nvme_vpd(self):
        for ip in nodes_ip:
            cmd = ["ipmitool", "-I", "lanplus", "-U", "admin", "-P", "admin", "-H", ip,
                   "raw", "0x30", "0xE1", "0x11", "0x00", "0x00", "0x4c"]
            result = subprocess.check_output(cmd)
            self.assertIn('4c 02 08', result, "can not obtain vpd")

    def test_nvme_health_data(self):
        for ip in nodes_ip:
            cmd = ["ipmitool", "-I", "lanplus", "-U", "admin", "-P", "admin", "-H", ip,
                   "raw", "0x30", "0xE3", "0x11"]
            result = subprocess.check_output(cmd)
            self.assertIn('30 1f 21', result, "can not obtain health data")

    def test_ntb(self):
        get_kernel_version = "uname -r"
        load_tranport = 'modprobe ntb_transport transport_mtu=2048'
        load_netdev = 'modprobe ntb_netdev'
        set_ip = 'ifconfig eth0 {} up'

        ver = run_cmd(get_kernel_version, nodes_ip[0])
        print("Running Kernel Version is {}.".format(ver))
        if int(ver.split('.')[1]) < 11:
            print("Quit test since kernel version less than 4.11")
            return

        run_cmd(load_tranport, nodes_ip[0])
        run_cmd(load_tranport, nodes_ip[1])

        run_cmd(load_netdev, nodes_ip[0])
        run_cmd(load_netdev, nodes_ip[1])

        run_cmd(set_ip.format("192.168.1.1"), nodes_ip[0])
        run_cmd(set_ip.format("192.168.1.2"), nodes_ip[1])

        line_a = run_cmd("ping -c 5 192.168.1.2", nodes_ip[0])
        line_b = run_cmd("ping -c 5 192.168.1.1", nodes_ip[1])

        self.assertNotIn("100% packet loss", line_a, line_a)
        self.assertNotIn("100% packet loss", line_b, line_b)
