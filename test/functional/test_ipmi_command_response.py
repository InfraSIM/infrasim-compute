#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test ipmitool commands work properly:
    - fru print
    - sensor list
    - user commnad
    - sel list
    - sdr list
    - check sel info entries count
    - ...
Check:
    - command return code
"""
import unittest
import os
import subprocess
import re
import time
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import CommandRunFailed

# ipmitool commands to test
cmd_prefix = 'ipmitool -H 127.0.0.1 -U admin -P admin '

fru_print_cmd = cmd_prefix + 'fru print'
lan_print_cmd = cmd_prefix + 'lan print'
sensor_list_cmd = cmd_prefix + 'sensor list'
sel_list_cmd = cmd_prefix + 'sel list'
sdr_list_cmd = cmd_prefix + 'sdr list'

user_list_cmd = cmd_prefix + 'user list'
user_compressed_list_cmd = cmd_prefix + '-c user list'
user_summary_cmd = cmd_prefix + 'user summary'

sel_clear_cmd = cmd_prefix + 'sel clear'
sel_info_cmd = cmd_prefix + 'sel info'


def run_command(cmd="", shell=True, stdin=None, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    return cmd_return_code, cmd_result


class test_ipmicommand_response(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        socat.start_socat()
        ipmi.start_ipmi("quanta_d51")
        time.sleep(3)

    @classmethod
    def tearDownClass(cls):
        qemu.stop_qemu()
        ipmi.stop_ipmi()
        socat.stop_socat()

    def test_fru_print(self):
        try:
            returncode, output = run_command(fru_print_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_lan_print(self):
        try:
            returncode, output = run_command(lan_print_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_sensor_list(self):
        try:
            returncode, output = run_command(sensor_list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_sel_list(self):
        try:
            returncode, output = run_command(sel_list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_sdr_list(self):
        try:
            returncode, output = run_command(sdr_list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_user_list(self):
        try:
            returncode, output = run_command(user_list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_user_compressed_list(self):
        try:
            returncode, output = run_command(user_compressed_list_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_user_summary(self):
        try:
            returncode, output = run_command(user_summary_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(returncode, 0)
        except:
            assert False

    def test_sel_info_entries_count_check(self):
        try:
            run_command(sel_clear_cmd)
            time.sleep(3)
            returncode, output = run_command(sel_info_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            str_out = str(output)
            self.assertIsNone(re.search('Entries(\s)*:(\s)*0', str_out))
        except:
            assert False

