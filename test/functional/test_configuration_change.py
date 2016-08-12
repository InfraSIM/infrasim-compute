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
        pass

    def test_set_cpu_family(self):
        pass

    def test_set_bmc_vendor(self):
        pass

    def test_set_memory_capacity(self):
        pass

    def test_set_disk_drive(self):
        pass
