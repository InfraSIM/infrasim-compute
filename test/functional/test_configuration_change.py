#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import unittest
import subprocess
import os
import yaml
from infrasim import config
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import model

PS_QEMU = "ps ax | grep qemu"
PS_IPMI = "ps ax | grep ipmi"
PS_SOCAT = "ps ax | grep socat"


def run_command(cmd="", shell=True, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell,
                             stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


class test_compute_configuration_change(unittest.TestCase):

    def setUp(self):
        os.system("touch test.yml")
        with open(config.infrasim_initial_config, 'r') as f_yml:
            self.conf = yaml.load(f_yml)
        self.conf["name"] = "test"

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        os.system("rm -rf test.yml")

    def test_set_vcpu(self):
        self.conf["compute"]["cpu"]["quantities"] = 8
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-smp 8" in str_result

    def test_set_cpu_family(self):
        self.conf["compute"]["cpu"]["type"] = "IvyBridge"
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-cpu IvyBridge" in str_result

    def test_set_memory_capacity(self):
        self.conf["compute"]["memory"]["size"] = 1536
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-m 1536" in str_result

    def test_set_disk_drive(self):
        self.conf["compute"]["storage_backend"] = [{
            "controller": {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8}, {"size": 8}]
            }
        }]
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert ".infrasim/sda.img,format=qcow2" in str_result
        assert ".infrasim/sdb.img,format=qcow2" in str_result

    def test_network_bridge_network(self):
        self.conf["compute"]["networks"][0]["network_mode"] = "bridge"
        self.conf["compute"]["networks"][0]["network_name"] = "fakebr0"
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        try:
            node = model.CNode(self.conf)
            node.init()
            node.precheck()
            node.start()
        except Exception as e:
            assert True

    def test_qemu_boot_from_disk_img(self):
        test_img_file = "{}/cirros-0.3.4-x86_64-disk.img".\
            format(os.environ['HOME'])
        if os.path.exists(test_img_file) is False:
            os.system("wget -c \
                http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img \
                -O {}".format(test_img_file))

        if os.path.exists(test_img_file) is False:
            assert False

        self.conf["compute"]["storage_backend"] = [{
            "controller": {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8, "file": test_img_file}]
            }
        }]
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        import telnetlib
        import paramiko
        import time
        tn = telnetlib.Telnet(host="127.0.0.1", port=2345)
        tn.read_until("(qemu)")
        tn.write("hostfwd_add ::2222-:22\n")
        tn.read_until("(qemu)")
        tn.close()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("filename.log")
        while True:
            try:
                ssh.connect("127.0.0.1", port=2222, username="cirros",
                        password="cubswin:)", timeout=120)
                ssh.close()
                break
            except paramiko.SSHException:
                time.sleep(1)
                continue
            except Exception as e:
                assert False
                return

        os.system("rm -rf {}".format(test_img_file))
        assert True


class test_bmc_configuration_change(unittest.TestCase):

    def setUp(self):
        os.system("touch test.yml")
        with open(config.infrasim_initial_config, 'r') as f_yml:
            self.conf = yaml.load(f_yml)
        self.conf["name"] = "test"

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        os.system("rm -rf test.yml")

    def test_set_bmc_iol_port(self):
        self.conf["bmc"] = {}
        self.conf["bmc"]["ipmi_over_lan_port"] = 624

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin -p 624 -I lanplus ' \
              'raw 0x06 0x01'
        returncode, output = run_command(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        assert returncode == 0

        cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin -p 623 -I lanplus ' \
              'raw 0x06 0x01'
        returncode, output = run_command(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        assert returncode != 0


class test_connection(unittest.TestCase):

    def setUp(self):
        os.system("touch test.yml")
        with open(config.infrasim_initial_config, 'r') as f_yml:
            self.conf = yaml.load(f_yml)
        self.conf["name"] = "test"
        self.bmc_conf = os.path.join(os.environ["HOME"], ".infrasim",
                                     "test", "data", "vbmc.conf")

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        os.system("rm -rf test.yml")

    def test_set_sol_device(self):
        temp_sol_device = "{}/.infrasim/pty_test".format(os.environ['HOME'])
        self.conf["sol_device"] = temp_sol_device

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_SOCAT, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "pty,link={},waitslave".format(temp_sol_device) in str_result

        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()
        assert 'sol "{}" 115200', format(temp_sol_device) in bmc_conf

    def test_set_ipmi_console_port(self):
        self.conf["ipmi_console_port"] = 9100

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()
        assert 'console 0.0.0.0 9100' in bmc_conf

        print '\033[93m{}\033[0m'.\
            format("Not implemented: "
                   "test if ipmi-console connect to same port")

    def test_set_bmc_connection_port(self):
        self.conf["bmc_connection_port"] = 9102

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()
        assert 'serial 15 0.0.0.0 9102 codec VM ipmb 0x20' in bmc_conf

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "port=9102" in str_result

    def test_set_serial_port(self):
        self.conf["serial_port"] = 9103

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "-serial mon:udp:127.0.0.1:9103,nowait" in str_result

        str_result = run_command(PS_SOCAT, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "udp-listen:9103,reuseaddr" in str_result

    def test_set_node_type(self):
        self.conf["type"] = "dell_c6320"

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-smbios file={}/.infrasim/test/data/dell_c6320_smbios.bin".\
            format(os.environ["HOME"]) in str_result

        str_result = run_command(PS_IPMI, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "-f {}/.infrasim/test/data/dell_c6320.emu".\
            format(os.environ["HOME"]) in str_result
