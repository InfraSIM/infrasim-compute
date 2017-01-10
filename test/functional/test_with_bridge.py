'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
import unittest
import re
from test import fixtures
from infrasim import run_command
from infrasim import CommandRunFailed
from infrasim import model

"""
This is a test file for every possible operation with bridge.
Generally, you use infrasim in NAT and may not additionally
create a bridge in your environment, while in this test, to
guaranttee infrasim works with bridge, I setup a bridge to
verify everything is fine.
I won't further make DHCP on that network so no things above
IP is put here.
"""


old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
try:
    ret, rsp = run_command("which brctl")
# There is no brctl, skip these test
except CommandRunFailed:
    raise unittest.SkipTest("No brctl is found in the environment")

FAKE_BRIDGE = "fakebr"
PS_QEMU = "ps ax | grep qemu"

# Pattern for mac address search
p = r"mac=(?P<mac>\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})"
r = re.compile(p)

# command prefix for test cases
cmd_prefix = 'ipmitool -I lanplus -H 127.0.0.1 -U admin -P admin chassis '
cmd_power_on = cmd_prefix + 'power on'
cmd_power_off = cmd_prefix + 'power off'
cmd_power_cycle = cmd_prefix + 'power cycle'
cmd_power_reset = cmd_prefix + 'power reset'
cmd_ps_qemu = 'ps ax | grep qemu'


def setup_module():
    os.environ["PATH"] = new_path

    # Setup bridge
    cmd = "brctl addbr {}".format(FAKE_BRIDGE)
    run_command(cmd)

    cmd = "ip link set dev {} up".format(FAKE_BRIDGE)
    run_command(cmd)

    cmd = "ifconfig {}".format(FAKE_BRIDGE)
    ret, rsp = run_command(cmd)
    if ret != 0 or FAKE_BRIDGE not in rsp:
        raise unittest.SkipTest("Fail to create fake bridge for test")


def teardown_module():

    # Destroy bridge
    cmd = "ip link set dev {} down".format(FAKE_BRIDGE)
    run_command(cmd)

    cmd = "brctl delbr {}".format(FAKE_BRIDGE)
    run_command(cmd)

    os.system("pkill socat")
    os.system("pkill ipmi")
    os.system("pkill qemu")
    os.environ["PATH"] = old_path


class test_node_with_bridge(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None

    def test_start_node(self):
        """
        Verify infrasim instance start with a ne
        """
        self.conf["compute"]["networks"].append(
            {
                "network_mode": "bridge",
                "network_name": FAKE_BRIDGE,
                "device": "vmxnet3",
                "mac": "00:11:22:33:44:55"
            }
        )

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        ret, rsp = run_command(PS_QEMU)
        assert "qemu-system-x86_64" in rsp
        assert "-netdev bridge,id=netdev1,br={}," \
               "helper=".format(FAKE_BRIDGE) in rsp
        assert "-device vmxnet3,netdev=netdev1," \
               "mac=00:11:22:33:44:55" in rsp


class test_mac_persist_on_bridge(unittest.TestCase):
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["networks"].append(
        {
            "network_mode": "bridge",
            "network_name": FAKE_BRIDGE,
            "device": "vmxnet3",
            "mac": "00:11:22:33:44:55"
        }
    )

    @classmethod
    def setUpClass(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.precheck()
        node.start()

    @classmethod
    def tearDownClass(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None

    def test_qemu_mac_persist_across_power_off_on(self):
        """
        Verify all network mac address persists across power off/on by ipmi command
        """
        # Get qemu mac addresses
        qemu_rsp = run_command(cmd_ps_qemu)[1]
        macs_former = r.findall(qemu_rsp)

        run_command(cmd_power_off)
        run_command(cmd_power_on)

        # Get qemu mac addresses
        qemu_rsp = run_command(cmd_ps_qemu)[1]
        macs_latter = r.findall(qemu_rsp)

        # Verify mac address list remains the same
        assert sorted(macs_former) == sorted(macs_latter)

    def test_qemu_mac_persist_across_power_cycle(self):
        """
        Verify all network mac address persists across power cycle by ipmi command
        """
        # Get qemu mac addresses
        qemu_rsp = run_command(cmd_ps_qemu)[1]
        macs_former = r.findall(qemu_rsp)

        run_command(cmd_power_cycle)

        # Get qemu mac addresses
        qemu_rsp = run_command(cmd_ps_qemu)[1]
        macs_latter = r.findall(qemu_rsp)

        # Verify mac address list remains the same
        assert sorted(macs_former) == sorted(macs_latter)

    def test_qemu_mac_persist_across_power_reset(self):
        """
        Verify all network mac address persists across power reset by ipmi command
        """
        # Get qemu mac addresses
        qemu_rsp = run_command(cmd_ps_qemu)[1]
        macs_former = r.findall(qemu_rsp)

        run_command(cmd_power_reset)

        # Get qemu mac addresses
        qemu_rsp = run_command(cmd_ps_qemu)[1]
        macs_latter = r.findall(qemu_rsp)

        # Verify mac address list remains the same
        assert sorted(macs_former) == sorted(macs_latter)

