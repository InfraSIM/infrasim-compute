#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test InfraSIM network configuration:
    - test_set_bridge(self): Set QEMU bridge mode
    - ...
"""
import unittest
import subprocess
import re
from infrasim import vm
from infrasim import ipmi

def run_command(cmd="", shell=True, stdout=None, stderr=None):
    """
    :param cmd: the command should run
    :param shell: if the type of cmd is string, shell should be set as True, otherwise, False
    :param stdout: reference subprocess module
    :param stderr: reference subprocess module
    :return: tuple (return code, output)
    """
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


class test_network(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        vm.stop_vm("quanta_d51")
        ipmi.stop_ipmi()

    def test_set_bridge(self):
        '''
        Set QEMU bridge mode
        '''
        #stop vm

        #get available nic
        ifconfig_cmd = "ifconfig"
        returncode, output = run_command(ifconfig_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        m = re.search('ens(\d*)\s|eth(\d*)\s', output)
        nic = m.group(0).replace(" ", "")

        #set to bridge mode
        v = vm.VM()
        v.set_network("bridge", nic)

        #start infrasim-vm
        vm.start_vm(v.render_vm_template())

        #check macvtap is up which means qemu is set to bridge mode
        ifconfig_cmd = "ifconfig"
        returncode_ifconfig, output_ifconfig = run_command(ifconfig_cmd,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
        self.assertIn("macvtap", output_ifconfig)
