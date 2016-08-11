#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import subprocess
import os
from infrasim import qemu


def run_command(cmd="", shell=True, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell,
                             stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


class test_configuration_change(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.system("touch test.yml")

    @classmethod
    def tearDownClass(cls):
        cmd = 'pkill qemu'
        run_command(cmd, True, None, None)
        os.system("rm -rf test.yml")

    def test_set_vcpu(self):
        vm = qemu.QEMU()
        os.system('echo "---" > test.yml')
        os.system('echo "node:" > test.yml')
        os.system('echo "    vcpu: 8" >> test.yml')
        vm.set_vcpu('test.yml')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)

        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
                                     subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result

    def test_set_cpu_family(self):
        vm = qemu.QEMU()
        os.system('echo "---" > test.yml')
        os.system('echo "node:" > test.yml')
        os.system('echo "    cpu: IvyBridge" >> test.yml')
        vm.set_cpu('test.yml')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)

        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
                                     subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result

    def test_set_bmc_vendor(self):
        vm = qemu.QEMU()
        os.system('echo "---" > test.yml')
        os.system('echo "main:" > test.yml')
        os.system('echo "    node: dell_c6320" >> test.yml')
        vm.set_node('test.yml')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)

        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
                                     subprocess.PIPE, subprocess.PIPE))
        assert '-name dell_c6320' in str_result

    def test_set_memory_capacity(self):
        vm = qemu.QEMU()
        os.system('echo "---" > test.yml')
        os.system('echo "node:" > test.yml')
        os.system('echo "    memory: 4096" >> test.yml')
        vm.set_memory('test.yml')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)

        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
                                     subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result

    def test_set_disk_drive(self):
        vm = qemu.QEMU()
        os.system('echo "---" > test.yml')
        os.system('echo "node:" > test.yml')
        os.system('echo "    disk_num: 2" >> test.yml')
        os.system('echo "    disk_size: 32" >> test.yml')
        vm.set_disks('test.yml')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)

        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
                                     subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result
