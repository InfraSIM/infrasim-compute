#!/usr/bin/env python
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
import traceback

from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import run_command

# command prefix for test cases
cmd_prefix = 'ipmitool -H 127.0.0.1 -U admin -P admin chassis '

# command to check if qemu is running
test_cmd = 'ps ax | grep qemu'

# get process id of qemu
pid_cmd = 'pidof qemu-system-x86_64'

# sleep 3 seconds
sleep_cmd = '; sleep 3s'

power_status_cmd = cmd_prefix + 'power status'
power_on_cmd = cmd_prefix + 'power on' + sleep_cmd
power_off_cmd = cmd_prefix + 'power off' + sleep_cmd
power_cycle_cmd = cmd_prefix + 'power cycle' + sleep_cmd
power_reset_cmd = cmd_prefix + 'power reset' + sleep_cmd


class test_ipmi_command_chassis_control(unittest.TestCase):
    def setUp(self):
        socat.start_socat()
        ipmi.start_ipmi("quanta_d51")
        time.sleep(3)

    def tearDown(self):
        qemu.stop_qemu()
        ipmi.stop_ipmi()
        socat.stop_socat()

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
        except:
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
        except:
            print traceback.format_exc()
            assert False

    def test_chassis_power_reset(self):
        try:
            pid_before = run_command(pid_cmd)[1]
            run_command(power_reset_cmd)
            qemu_output = run_command(test_cmd)[1]
            assert 'qemu-system-x86_64' in qemu_output
            pid_after = run_command(pid_cmd)[1]
            assert pid_after != pid_before
        except:
            print traceback.format_exc()
            assert False
