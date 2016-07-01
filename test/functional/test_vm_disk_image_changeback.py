#!/usr/bin/env python 
# -*- coding: utf-8 -*-
"""
this script is used to check the disk image size which is changed from other values to default (4G)

author: payne.wang@emc.com
"""

import subprocess
import re
import os
from infrasim import vm

v = vm.VM()


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

def get_disk_image_size(disk_image_path):
    disk_size_cmd = "qemu-img info {} | grep 'virtual size:'".\
                format(disk_image_path)
    disk_size_returncode, disk_size_result = \
                run_command(disk_size_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    return disk_size_result.strip()


def change_disk_image_size(image_size): 
    stop_vm()
    v.set_sata_disks_with_size(1, image_size)
    start_vm()


def start_vm():
    vm.start_vm(v.render_vm_template())


def stop_vm():
    if vm.check_vm_status("quanta_d51"):
        vm.stop_vm("quanta_d51")


# change disk image size to 8G and change back to default (4G)
def test_vm_disk_size_changeto_8G_and_changeto_default():
    home = os.environ["HOME"]
    disk_image_path = "{}/.infrasimsda.img".format(home) # only one image is created
    change_disk_image_size(8)
    expect_value = "virtual size: 8.0G (8589934592 bytes)"
    disk_size_result = get_disk_image_size(disk_image_path)
    assert disk_size_result == expect_value

    change_disk_image_size(4)
    expect_value = "virtual size: 4.0G (4294967296 bytes)"
    disk_size_result = get_disk_image_size(disk_image_path)
    assert disk_size_result == expect_value
    stop_vm()
