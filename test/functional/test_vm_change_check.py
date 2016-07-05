#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
this script is used to check the changed value of Infrasim

change Memory size to 128M and check
change Memory size to 256M and check
change Memory size to 1024M and check
change Memory size to 2048M and check

change CPU count to 1 and check
change CPU count to 6 and check

change disk count to 2 and check
change disk size to 8G and check

author: payne.wang@emc.com
"""

import subprocess
import re
from infrasim import vm
from infrasim import qemu
from infrasim import run_command

v = vm.VM()
qemu = qemu.Qemu()


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


def start_vm():
    vm.start_vm(v.render_vm_template())
    qemu_cmd = "ps ax | grep qemu"
    return run_command(qemu_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def stop_vm():
    vm.stop_vm("quanta_d51")


class Test_VM_Change_Mem_Size:
    @classmethod
    def setup_class(cls):
        start_vm()
        sys_mem_cmd = "grep MemTotal /proc/meminfo | awk '{print $2}'"
        sys_mem_returncode, cls.sys_mem_size = run_command(sys_mem_cmd,
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE)
    
    @classmethod
    def teardown_class(cls):
        stop_vm()

    def mem_set_check(self, set_mem_size, check_mem_size_pat):
        if int(self.sys_mem_size) < set_mem_size*1024:
            assert True
            print "can't set {} MB Memory size because system memory is {} MB"\
                .format(set_mem_size, int(self.sys_mem_size)/1024)
            return

        global v
        stop_vm()
        v.set_memory_size(mem_size=set_mem_size)
        returncode, output = start_vm()
        try:
            re.search("-m {}".format(check_mem_size_pat), output).group()
        except AttributeError:
            assert False
        else:
            assert True

    def test_vm_mem_changeto_128M(self):
        self.mem_set_check(128, "1\d{2}")

    def test_vm_mem_changeto_256M(self):
        self.mem_set_check(256, "2\d{2}")

    def test_vm_mem_changeto_1024M(self):
        self.mem_set_check(1024, "9\d{2}")

    def test_vm_mem_changeto_2048M(self):
        self.mem_set_check(2048, "19\d{2}")


class Test_VM_Change_CPU_Count:
    @classmethod
    def setup_class(cls):
        start_vm()

    @classmethod
    def teardown_class(cls):
        stop_vm()

    @staticmethod
    def cpu_set_check(cpu_count):
        stop_vm()
        v.set_vcpu_num(cpu_count)
        returncode, output = start_vm()
        cpu_count = "-smp {smp},sockets={sockets},cores={cores}," \
                    "threads={threads}".format(
            smp=cpu_count, sockets=cpu_count, cores=1, threads=1)
        assert cpu_count in output

    def test_vm_cpu_count_changeto_1(self):
        self.cpu_set_check(1)

    def test_vm_cpu_count_changeto_6(self):
        self.cpu_set_check(6)


class Test_VM_Change_Disk:
    @classmethod
    def setup_class(cls):
        start_vm()

    @classmethod
    def teardown_class(cls):
        stop_vm()

    def test_vm_disk_count_changeto_2(self):
        stop_vm()
        v.set_sata_disks_with_size(2)
        returncode, output = start_vm()
        disk_count = 0
        qemu_parameters = output.split()
        for parameter in qemu_parameters:
            if parameter.startswith("file=") and ".img" in parameter:
                disk_count += 1
        assert disk_count == 2

    def test_vm_disk_size_changeto_8G(self):
        stop_vm()
        v.set_sata_disks_with_size(1, 8)
        returncode, output = start_vm()
        qemu_parameters = output.split()
        for parameter in qemu_parameters:
            if parameter.startswith("file=") and ".img" in parameter:
                disk_image_path = parameter.split(",")[0].split("=")[1]
                disk_size_cmd = "qemu-img info {} | grep 'virtual size:'".\
                    format(disk_image_path)
                disk_size_returncode, disk_size_result = \
                    run_command(disk_size_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
                expect_value = "virtual size: 8.0G (8589934592 bytes)"
                assert disk_size_result.strip() == expect_value



