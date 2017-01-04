'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import time
import re
from infrasim import model
from infrasim import run_command
from test import fixtures


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

# command to check if qemu is running
test_cmd = 'ps ax | grep qemu'

# get process id of qemu
pid_cmd = 'pidof qemu-system-x86_64'

power_status_cmd = cmd_prefix + 'power status'
power_on_cmd = cmd_prefix + 'power on'
power_off_cmd = cmd_prefix + 'power off'
power_cycle_cmd = cmd_prefix + 'power cycle'
power_reset_cmd = cmd_prefix + 'power reset'


# Pattern for mac address search
p = r"mac=(?P<mac>\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})"
r = re.compile(p)


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
            qemu_output = run_command(test_cmd)[1]
            assert 'Chassis Power is on' in status_output
            assert 'qemu-system-x86_64' in qemu_output

            # Get qemu mac addresses
            macs_former = r.findall(qemu_output)

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

            # Get qemu mac addresses again
            macs_latter = r.findall(qemu_output)

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
            qemu_output = run_command(test_cmd)[1]
            macs_former = r.findall(qemu_output)

            pid_before = run_command(pid_cmd)[1]
            run_command(power_cycle_cmd)
            qemu_output = run_command(test_cmd)[1]
            assert 'qemu-system-x86_64' in qemu_output
            pid_after = run_command(pid_cmd)[1]
            assert pid_after != pid_before

            # Get qemu mac addresses again
            qemu_output = run_command(test_cmd)[1]
            macs_latter = r.findall(qemu_output)

            # Verify mac address list remains the same
            assert sorted(macs_former) == sorted(macs_latter)

        except Exception as e:
            print e
            assert False

    def test_chassis_power_reset(self):
        try:
            # Get qemu mac addresses
            qemu_output = run_command(test_cmd)[1]
            macs_former = r.findall(qemu_output)

            pid_before = run_command(pid_cmd)[1]
            run_command(power_reset_cmd)
            qemu_output = run_command(test_cmd)[1]
            assert 'qemu-system-x86_64' in qemu_output
            pid_after = run_command(pid_cmd)[1]
            assert pid_after != pid_before

            # Get qemu mac addresses again
            qemu_output = run_command(test_cmd)[1]
            macs_latter = r.findall(qemu_output)

            # Verify mac address list remains the same
            assert sorted(macs_former) == sorted(macs_latter)

        except Exception as e:
            print e
            assert False
