#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
this script is used to check the value of Infrasim app default configuration
default values checking:
    vm status: running
    vm cpu count: 4
    vm disk count: 1
    vm disk size: 4G
    vm network: nat
    vm memory size: 512M

author: payne.wang@emc.com
"""

import subprocess
import re
import os
from nose.tools import with_setup
from infrasim import vm


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


class Test_Default_VM:
    @classmethod
    def setup_class(cls):
        # remove the existing disk image
        disk_image_path = "{}/.infrasimsda.img".format(os.environ["HOME"])
        if os.path.exists(disk_image_path):
            os.remove(disk_image_path)
        v = vm.VM()
        vm.start_vm(v.render_vm_template())
        qemu_cmd = "ps ax | grep qemu"
        cls.returncode, cls.output = run_command(qemu_cmd,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
    
    @classmethod
    def teardown_class(cls):
        vm.stop_vm("quanta_d51")
         
    def test_vm_status(self):
        vm_status = vm.check_vm_status("quanta_d51")
        assert vm_status is True

    def test_cpu_count_4(self):
        expect_cpu_info = "-smp 4,sockets=4,cores=1,threads=1"
        assert expect_cpu_info in self.output

    def test_cpu_type_haswell(self):
        # TODO: should find a way to check type of CPU
        pass

    def test_disk_count_1(self):
        disk_count = 0
        qemu_parameters = self.output.split()
        for parameter in qemu_parameters:
            if parameter.startswith("file=") and ".img" in parameter:
                disk_count += 1
        assert disk_count == 1

    def test_disk_size_4G(self):
        qemu_parameters = self.output.split()
        for parameter in qemu_parameters:
            if parameter.startswith("file=") and ".img" in parameter:
                disk_image_path = parameter.split(",")[0].split("=")[1]
                disk_size_cmd = "qemu-img info {} | grep 'virtual size:'".\
                    format(disk_image_path)
                disk_size_returncode, disk_size_result = \
                    run_command(disk_size_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
                assert disk_size_result.strip() == \
                       "virtual size: 4.0G (4294967296 bytes)"

    def test_network_nat(self):
        network_cmd = "ifconfig | grep vnet0"  # vnet0 should exist if network is nat
        network_returncode, network_output = \
            run_command(network_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
        assert network_output

    def test_mem_size_512M(self):
        mem_size_pat = "-m 4\d{2}"
        try:
            re.search(mem_size_pat, self.output).group()
        except AttributeError:
            assert False
        else:
            assert True
