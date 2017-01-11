'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
import unittest
import re
import time
import paramiko
from test import fixtures
from infrasim import run_command
from infrasim import CommandRunFailed, InfraSimError
from infrasim import model
from infrasim import helper

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


class test_bmc_interface_with_bridge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            helper.fetch_image(
                "https://github.com/InfraSIM/test/raw/master/image/kcs.img",
                "cfdf7d855d2f69c67c6e16cc9b53f0da", "/tmp/kcs.img")
        except InfraSimError, e:
            print e.value

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()
        self.conf["compute"]["storage_backend"] = [{
            "controller": {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"file": "/tmp/kcs.img"}]
            }
        }]

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None

    def set_port_forward(self):
        time.sleep(3)
        import telnetlib
        tn = telnetlib.Telnet(host="127.0.0.1", port=2345)
        tn.read_until("(qemu)")
        tn.write("hostfwd_add ::2222-:22\n")
        tn.read_until("(qemu)")
        tn.close()

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("filename.log")
        while True:
            try:
                ssh.connect("127.0.0.1", port=2222, username="root",
                            password="root", timeout=120)
                ssh.close()
                break
            except paramiko.SSHException:
                time.sleep(1)
                continue
            except Exception:
                assert False

        time.sleep(5)

    def verify_qemu_local_lan(self, expects):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("127.0.0.1", port=2222, username="root",
                    password="root", timeout=10)

        for key, val in expects.iteritems():
            stdin, stdout, stderr = ssh.exec_command("ipmitool lan print | grep '{}'".format(key))
            while not stdout.channel.exit_status_ready():
                pass
            lines = stdout.channel.recv(2048)
            print lines
            assert val in lines

        ssh.close()

    def test_bmc_intf_not_exists(self):
        """
        BMC will not bind to any interface if specified BMC interfaces doesn't exist
        """
        self.conf["bmc"] = {
            "interface": "nonexists"
        }
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        self.set_port_forward()
        self.verify_qemu_local_lan({"IP Address": "0.0.0.0", "MAC Address":"00:00:00:00:00:00"})

    def test_bmc_intf_exists_no_ip(self):
        """
        BMC will bind to specified interface with ip 0.0.0.0 if this interface has no ip address
        """
        self.conf["bmc"] = {
            "interface": FAKE_BRIDGE
        }
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        mac_addr = run_command("cat /sys/class/net/{}/address".format(FAKE_BRIDGE))[1]
        self.set_port_forward()
        self.verify_qemu_local_lan(
            {"IP Address": "0.0.0.0", "MAC Address": "{}".format(mac_addr)})

    def test_bmc_intf_exists_has_ip(self):
        """
        BMC will bind to specified interface and accessed through lanplus channel when interface has valid ip address
        """
        interface = None
        interface_ip = None
        intf_list = helper.get_all_interfaces()

        # look up an interface with valid ip address
        for intf in intf_list:
            interface_ip = helper.get_interface_ip(intf)
            if intf == "lo" or not interface_ip:
                continue
            interface = intf
            break

        # if no interface has ip, skip this test
        if not interface:
            self.skipTest("No interface has IP in the environment, skip this test.")
        self.conf["bmc"] = {
            "interface": interface
        }
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        mac_addr = run_command(
            "cat /sys/class/net/{}/address".format(interface))[1]

        lan_print_rst = run_command(
            "ipmitool -U admin -P admin -H {} lan print".format(interface_ip))[1]

        assert mac_addr in lan_print_rst
