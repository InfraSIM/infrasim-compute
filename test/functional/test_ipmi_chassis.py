#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

"""
Test ipmitool chassis control commands:
    chassis power Commands:
    - status
    - on
    - off
    - cycle
    - reset
"""

import unittest
import time
import yaml

from infrasim import model
from infrasim import run_command
from infrasim import config

# command prefix for test cases
cmd_prefix = 'ipmitool -I lanplus -H 127.0.0.1 -U admin -P admin chassis '

# command to check if qemu is running
test_cmd = 'ps ax | grep qemu'

# get process id of qemu
pid_cmd = 'pidof qemu-system-x86_64'

power_status_cmd = cmd_prefix + 'power status'
power_on_cmd = cmd_prefix + 'power on'
power_off_cmd = cmd_prefix + 'power off'
power_cycle_cmd = cmd_prefix + 'power cycle'
power_reset_cmd = cmd_prefix + 'power reset'


class test_ipmi_command_chassis_control(unittest.TestCase):
    def setUp(self):
        node_info = {}
        with open(config.infrasim_initial_config, 'r') as f_yml:
            node_info = yaml.load(f_yml)
        node_info["name"] = "test"
        node = model.CNode(node_info)
        node.init()
        node.precheck()
        node.start()
        # FIXME: sleep is not a good way to wait qemu starts up.
        time.sleep(3)

    def tearDown(self):
        node_info = {}
        with open(config.infrasim_initial_config, 'r') as f_yml:
            node_info = yaml.load(f_yml)
        node_info["name"] = "test"
        node = model.CNode(node_info)
        node.init()
        node.stop()
        node.terminate_workspace()

    def test_chassis_power_off_on(self):
        try:
            status_output = run_command(power_status_cmd)[1]
            qemu_output = run_command(test_cmd)[1]
            assert 'Chassis Power is on' in status_output
            assert 'qemu-system-x86_64' in qemu_output

            run_command(power_off_cmd)
            qemu_output = run_command(test_cmd)[1]
            status_output = run_command(power_status_cmd)[1]
            assert 'Chassis Power is off' in status_output
            assert 'qemu-system-x86_64' not in qemu_output

            run_command(power_on_cmd)
            qemu_output = run_command(test_cmd)[1]
            status_output = run_command(power_status_cmd)[1]
            assert 'Chassis Power is on' in status_output
            assert 'qemu-system-x86_64' in qemu_output
        except Exception as e:
            print e
            import traceback
            print traceback.format_exc()
            assert False

    def test_chassis_power_cycle(self):
        try:
            pid_before = run_command(pid_cmd)[1]
            run_command(power_cycle_cmd)
            qemu_output = run_command(test_cmd)[1]
            assert 'qemu-system-x86_64' in qemu_output
            pid_after = run_command(pid_cmd)[1]
            assert pid_after != pid_before
        except Exception as e:
            print e
            assert False

    def test_chassis_power_reset(self):
        try:
            pid_before = run_command(pid_cmd)[1]
            run_command(power_reset_cmd)
            qemu_output = run_command(test_cmd)[1]
            assert 'qemu-system-x86_64' in qemu_output
            pid_after = run_command(pid_cmd)[1]
            assert pid_after != pid_before
        except Exception as e:
            print e
            assert False
