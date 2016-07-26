#!/usr/bin/env python 
# -*- coding: utf-8 -*-


import unittest
import subprocess
import netifaces
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
        pass

    @classmethod
    def tearDownClass(cls):
        cmd = 'pkill qemu'
        run_command(cmd, True, None, None)

    def test_set_vcpu(self):
        vm = qemu.QEMU()
        os.system('echo "[node]" > test.config')
        os.system('echo "vcpu=8" >> test.config')
        vm.set_vcpu('test.config')
        cmd = vm.get_qemu_cmd()
        return_code, result = run_command(cmd, True,
                subprocess.PIPE, subprocess.PIPE)

        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
            subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result

    def test_set_cpu_family(self):
        vm = qemu.QEMU()
        os.system('echo "[node]" > test.config')
        os.system('echo "cpu=IvyBridge" >> test.config')
        vm.set_cpu('test.config')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)
 
        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
            subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result

    def test_set_bmc_vendor(self):
        vm = qemu.QEMU()
        os.system('echo "[main]" > test.config')
        os.system('echo "node=dell_c6320" >> test.config')
        vm.set_node('test.config')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)
 
        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
            subprocess.PIPE, subprocess.PIPE))
        assert '-name dell_c6320' in str_result

    def test_set_memory_capacity(self):
        vm = qemu.QEMU()
        os.system('echo "[node]" > test.config')
        os.system('echo "memory=4096" >> test.config')
        vm.set_memory('test.config')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)
 
        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
            subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result

    def test_set_disk_drive(self):
        vm = qemu.QEMU()
        os.system('echo "[node]" > test.config')
        os.system('echo "disk_num=2" >> test.config')
        os.system('echo "disk_size=32" >> test.config')
        vm.set_disks('test.config')
        cmd = vm.get_qemu_cmd()
        run_command(cmd, True, None, None)
 
        test_cmd = 'ps ax | grep qemu'
        str_result = str(run_command(test_cmd, True,
            subprocess.PIPE, subprocess.PIPE))
        assert 'qemu-system-x86_64' in str_result
 
