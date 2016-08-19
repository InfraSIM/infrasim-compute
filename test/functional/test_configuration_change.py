#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import subprocess
import os
import yaml
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat

VM_DEFAULT_CONFIG = "/etc/infrasim/infrasim.yml"
CMD = "ps ax | grep qemu"


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
        with open(VM_DEFAULT_CONFIG, 'r') as f_yml:
            self.conf = yaml.load(f_yml)

    def tearDown(self):
        self.conf = None
        cmd = 'pkill qemu'
        run_command(cmd, True, subprocess.PIPE, subprocess.PIPE)
        os.system("rm -rf test.yml")

    def test_set_vcpu(self):
        self.conf["compute"]["cpu"]["quantities"] = 8
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        qemu.start_qemu("test.yml")
        str_result = run_command(CMD, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-smp 8" in str_result

    def test_set_cpu_family(self):
        self.conf["compute"]["cpu"]["type"] = "IvyBridge"
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        qemu.start_qemu("test.yml")
        str_result = run_command(CMD, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-cpu IvyBridge" in str_result

    def test_set_node_name(self):
        self.conf["compute"]["name"] = "dell_c6320"
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        qemu.start_qemu("test.yml")
        str_result = run_command(CMD, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-name dell_c6320" in str_result
        assert "-smbios file=/usr/local/etc/infrasim/" \
               "dell_c6320/dell_c6320_smbios.bin" in str_result

    def test_set_memory_capacity(self):
        self.conf["compute"]["memory"]["size"] = 2048
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        qemu.start_qemu("test.yml")
        str_result = run_command(CMD, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-m 2048" in str_result

    def test_set_disk_drive(self):
        self.conf["compute"]["drives"] = [
            {"size": 32},
            {"size": 32}
        ]
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        qemu.start_qemu("test.yml")
        str_result = run_command(CMD, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert ".infrasim/sda.img,format=qcow2" in str_result
        assert ".infrasim/sdb.img,format=qcow2" in str_result


class test_bmc_configuration_change(unittest.TestCase):

    def setUp(self):
        os.system("touch test.yml")
        with open(VM_DEFAULT_CONFIG, 'r') as f_yml:
            self.conf = yaml.load(f_yml)

    def tearDown(self):
        self.conf = None
        qemu.stop_qemu()
        ipmi.stop_ipmi()
        socat.stop_socat()
        os.system("rm -rf test.yml")

    def test_set_bmc_iol_port(self):
        self.conf["bmc"] = {}
        self.conf["bmc"]["ipmi_over_lan_port"] = 624
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        socat.start_socat()
        ipmi.start_ipmi("test.yml")

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
