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
from infrasim import vm
from infrasim import ipmi


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
    print 'cmd_result:', cmd_result
    print 'child.returncode:', child.returncode
    return cmd_return_code, cmd_result


class test_ipmicommand_response(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ipmi.ipmi_start()

    @classmethod
    def tearDownClass(cls):
        ipmi.ipmi_stop()
        time.sleep(3)

    def test_fru_print(self):
        returncode, output = run_command(fru_print_cmd)
        self.assertEqual(returncode, 0)

    def test_lan_print(self):
        returncode, output = run_command(lan_print_cmd)
        self.assertEqual(returncode, 0)

    def test_sensor_list(self):
        returncode, output = run_command(sensor_list_cmd)
        self.assertEqual(returncode, 0)

    def test_sel_list(self):
        returncode, output = run_command(sel_list_cmd)
        self.assertEqual(returncode, 0)

    def test_sdr_list(self):
        returncode, output = run_command(sdr_list_cmd)
        self.assertEqual(returncode, 0)

    def test_user_list(self):
        returncode, output = run_command(user_list_cmd)
        self.assertEqual(returncode, 0)

    def test_user_compressed_list(self):
        returncode, output = run_command(user_compressed_list_cmd)
        self.assertEqual(returncode, 0)

    def test_user_summary(self):
        returncode, output = run_command(user_summary_cmd)
        self.assertEqual(returncode, 0)

    def test_sel_info_entries_count_check(self):
        run_command(sel_clear_cmd)
        time.sleep(3)
        returncode, output = run_command(sel_info_cmd)
        str_out = str(output)
        self.assertIsNone(re.search('Entries(\s)*:(\s)*0', str_out))

