'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import time
import re
import os
from infrasim import model
from infrasim import run_command
from test import fixtures
from infrasim import config


"""
Test ipmitool chassis control commands:
    chassis power Commands:
    - status
    - on
    - off
    - cycle
    - reset
"""

# command prefix for test cases
cmd_prefix = 'ipmitool -I lanplus -H 127.0.0.1 -U admin -P admin chassis '

# get process id of qemu
power_status_cmd = cmd_prefix + 'power status'
power_on_cmd = cmd_prefix + 'power on'
power_off_cmd = cmd_prefix + 'power off'
power_cycle_cmd = cmd_prefix + 'power cycle'
power_reset_cmd = cmd_prefix + 'power reset'

# Pattern for mac address search
p = r"mac=(?P<mac>\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})"
r = re.compile(p)


def get_mac():
    pid = get_qemu_pid()
    if pid == "":
        return ""

    cmdline = ""
    qemu_cmdline = "/proc/{}/cmdline".format(pid)
    with open(qemu_cmdline) as fd:
        cmdline = fd.readline()
    return r.findall(cmdline)


def get_qemu_pid():
    pid = ""
    pid_path = os.path.join(config.infrasim_home, "test/.test-node.pid")
    if not os.path.exists(pid_path):
        return ""

    with open(os.path.join(config.infrasim_home, "test/.test-node.pid")) as fd:
        pid = fd.readline().strip()

    return pid


class test_ipmi_command_chassis_control(unittest.TestCase):
    def setUp(self):
        self.node_info = {}
        fake_config = fixtures.FakeConfig()
        self.node_info = fake_config.get_node_info()
        node = model.CNode(self.node_info)
        node.init()
        node.precheck()
        node.start()
        # FIXME: sleep is not a good way to wait qemu starts up.
        time.sleep(3)

    def tearDown(self):
        node = model.CNode(self.node_info)
        node.init()
        node.stop()
        node.terminate_workspace()

    def test_chassis_power_off_on(self):
        try:
            status_output = run_command(power_status_cmd)[1]
            assert 'Chassis Power is on' in status_output
            pid = get_qemu_pid()
            assert pid != ""
            assert os.path.exists("/proc/{}".format(pid))

            # Get qemu mac addresses
            macs_former = get_mac()

            run_command(power_off_cmd)
            status_output = run_command(power_status_cmd)[1]
            assert 'Chassis Power is off' in status_output
            pid = get_qemu_pid()
            assert pid == ""

            run_command(power_on_cmd)
            time.sleep(2.5)
            status_output = run_command(power_status_cmd)[1]
            assert 'Chassis Power is on' in status_output
            pid = get_qemu_pid()
            assert pid != ""
            assert os.path.exists("/proc/{}".format(pid))

            # Get qemu mac addresses again
            macs_latter = get_mac()
            # Verify mac address list remains the same
            assert sorted(macs_former) == sorted(macs_latter)

        except Exception as e:
            print e
            import traceback
            print traceback.format_exc()
            assert False

    def test_chassis_power_cycle(self):
        try:
            # Get qemu mac addresses
            macs_former = get_mac()

            pid_before = get_qemu_pid()
            run_command(power_cycle_cmd)
            time.sleep(2.5)
            pid = get_qemu_pid()
            assert pid != ""
            assert os.path.exists("/proc/{}".format(pid))
            pid_after = get_qemu_pid()
            assert pid_after != pid_before

            # Get qemu mac addresses again
            macs_latter = get_mac()

            # Verify mac address list remains the same
            assert sorted(macs_former) == sorted(macs_latter)

        except Exception as e:
            print e
            assert False

    def test_chassis_power_reset(self):
        try:
            # Get qemu mac addresses
            macs_former = get_mac()

            pid_before = get_qemu_pid()
            assert pid_before != ""
            assert os.path.exists("/proc/{}".format(pid_before))

            run_command(power_reset_cmd)

            time.sleep(2.5)
            pid_after = get_qemu_pid()
            assert pid_after != ""
            assert os.path.exists("/proc/{}".format(pid_after))

            assert pid_after != pid_before

            # Get qemu mac addresses again
            macs_latter = get_mac()

            # Verify mac address list remains the same
            assert sorted(macs_former) == sorted(macs_latter)

        except Exception as e:
            print e
            assert False
