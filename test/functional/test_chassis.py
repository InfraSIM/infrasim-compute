'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import pprint
import os
import time
import yaml
import shutil
from infrasim import model
from infrasim import helper
from infrasim import InfraSimError
import paramiko
from test import fixtures

a_boot_image = "/home/infrasim/jenkins/data/ubuntu14.04.4.qcow2"
b_boot_image = "/home/infrasim/jenkins/data/ubuntu14.04.4_b.qcow2"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None
conf = {}
chassis = None


def setup_module():
    os.environ["PATH"] = new_path
    if os.path.exists(a_boot_image) is False:
        raise Exception("Not found image {}".format(a_boot_image))
    if os.path.exists(b_boot_image) is False:
        shutil.copy(a_boot_image, b_boot_image)
    with open("/tmp/trace_items", "w") as fo:
        fo.write("comm_log\n")
        fo.write("comm_failed\n")


def teardown_module():
    global conf
    if conf:
        stop_chassis()
    os.environ["PATH"] = old_path


def start_chassis():
    """
    
    """
    global conf
    global ssh

    conf = fixtures.ChassisConfig().get_chassis_info()
    node0_log = "/tmp/qemu_node0.log"
    node1_log = "/tmp/qemu_node1.log"
    compute_0 = conf["nodes"][0]["compute"]
    compute_0["storage_backend"][0]["drives"][0]["file"] = a_boot_image
    compute_0["extra_option"] = "-D {} -trace events=/tmp/trace_items".format(node0_log)

    compute_1 = conf["nodes"][1]["compute"]
    compute_1["storage_backend"][0]["drives"][0]["file"] = b_boot_image
    compute_1["extra_option"] = "-D {} -trace events=/tmp/trace_items".format(node1_log)

    conf["data"]["sn"] = "WHAT_EVER_SN"
    conf["data"]["psu1_pn"] = "A380-B737-C909"

    if os.path.exists(node0_log):
        os.remove(node0_log)
    if os.path.exists(node1_log):
        os.remove(node1_log)

    global chassis
    chassis = model.CChassis(conf["name"], conf)
    chassis.precheck()
    chassis.init()
    chassis.start()

    ssh = helper.prepare_ssh("192.168.188.92", 8022)


def stop_chassis():
    global conf
    global tmp_conf_file
    global chassis
    if chassis:
        chassis.destroy()
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
        self.assertIn("in [commu_internal_check], chassis/psu1_pn=A380-B737-C909", rst,
                      "Can't get information from shared memory!")
        self.assertIn("in [commu_internal_check], chassis/sn=WHAT_EVER_SN", rst,
                      "Can't get information from shared memory!")

        with open("/tmp/qemu_node1.log") as fi:
            rst = fi.read()
        self.assertIn("in [commu_internal_check], chassis/psu1_pn=A380-B737-C909", rst,
                      "Can't get information from shared memory!")
        self.assertIn("in [commu_internal_check], chassis/sn=WHAT_EVER_SN", rst,
                      "Can't get information from shared memory!")

