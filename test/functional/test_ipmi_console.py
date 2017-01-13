#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import unittest
import subprocess
import os
import time
import paramiko
from infrasim import console
from infrasim import config
from infrasim.model import CNode
from infrasim.config_manager import NodeMap
from test import fixtures
import threading
import yaml
import shutil
import telnetlib
import socket
import signal
from test.fixtures import FakeConfig


def run_command(cmd="", shell=True, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


def read_buffer(channel):
    while not channel.recv_ready():
        continue
    str_output = ''
    str_read = ''
    while True:
        str_read = str(channel.recv(40960))
        str_output += str_read
        if str_output.find('IPMI_SIM>\n'):
            break
        time.sleep(1)
    return str_output


def reset_console(channel, timeout=10):
    # Clear all output first
    while channel.recv_ready():
        channel.recv(4096)
        time.sleep(0.1)

    # Send ENTER and wait for a new prompt
    start = time.time()
    str_output = ''
    channel.send('\n')
    while True:
        str_output += str(channel.recv(4096))
        if str_output.find('IPMI_SIM>\n'):
            return
        time.sleep(0.1)
        if time.time() - start > timeout:
            raise RuntimeError('ipmi-console reset expires {}s'.
                               format(timeout))


class test_ipmi_console_start_stop(unittest.TestCase):

    def tearDown(self):
        os.system("infrasim node destroy {}".format(self.node_name))
        os.system("rm -rf {}".format(self.node_workspace))
        os.system("pkill socat")
        os.system("pkill ipmi")
        os.system("pkill qemu")

    def test_start_stop_default_ipmi_console(self):
        self.node_name = "default"
        self.node_workspace = os.path.join(config.infrasim_home, self.node_name)
        os.system("infrasim node start")
        os.system("ipmi-console start")
        ipmi_start_cmd = 'ps ax | grep ipmi-console'
        returncode, output = run_command(ipmi_start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.system("ipmi-console stop")
        ipmi_stop_cmd = 'ps ax | grep ipmi-console'
        returncode1, output1 = run_command(ipmi_stop_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(returncode, 0)
        assert 'ipmi-console start' in output
        self.assertEqual(returncode1, 0)
        assert 'ipmi-console start' not in output1

    def test_start_stop_specified_ipmi_console(self):
        self.node_name = "test"
        self.node_workspace = os.path.join(config.infrasim_home, self.node_name)
        node_config_path = "test.yml"
        node_info = FakeConfig().get_node_info()
        with open(node_config_path, "w") as fp:
            yaml.dump(node_info, fp, default_flow_style=False)
        os.system("infrasim config add {} {}".format(self.node_name, node_config_path))
        os.system("infrasim node start {}".format(self.node_name))
        os.system("ipmi-console start {}".format(self.node_name))
        ipmi_start_cmd = 'ps ax | grep ipmi-console'
        returncode, output = run_command(ipmi_start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.system("ipmi-console stop {}".format(self.node_name))
        ipmi_stop_cmd = 'ps ax | grep ipmi-console'
        returncode1, output1 = run_command(ipmi_stop_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(returncode, 0)
        self.assertEqual(returncode, 0)
        assert 'ipmi-console start {}'.format(self.node_name) in output
        self.assertEqual(returncode1, 0)
        assert 'ipmi-console start {}'.format(self.node_name) not in output1
        node_map = NodeMap()
        node_map.delete(self.node_name)

    def test_start_ipmi_console_not_start_bmc(self):
        self.node_name = "default"
        self.node_workspace = os.path.join(config.infrasim_home, self.node_name)
        os.system("infrasim node start")
        os.system("infrasim node stop")
        ipmi_start_cmd = 'ipmi-console start'
        returncode, output = run_command(ipmi_start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(returncode, 0)
        assert 'Warning: node default has not started BMC. Please start node default first.' in output
        ipmi_start_cmd = 'ps ax | grep ipmi-console'
        returncode, output = run_command(ipmi_start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.system("ipmi-console stop")
        self.assertEqual(returncode, 0)
        assert 'ipmi-console start' not in output

    def test_start_ipmi_console_no_workspace(self):
        self.node_name = "default"
        self.node_workspace = os.path.join(config.infrasim_home, self.node_name)
        ipmi_start_cmd = 'ipmi-console start'
        returncode, output = run_command(ipmi_start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(returncode, 0)
        assert 'Warning: there is no node default workspace. Please start node default first.' in output
        ipmi_start_cmd = "ps ax | grep ipmi-console"
        returncode, output = run_command(ipmi_start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(returncode, 0)
        assert 'ipmi-console start' not in output


class test_ipmi_console(unittest.TestCase):

    ssh = paramiko.SSHClient()
    channel = None
    # Just for quanta_d51
    sensor_id = '0xc0'
    sensor_value = '1000.00'
    event_id = '6'
    TMP_CONF_FILE = "/tmp/test.yml"

    @classmethod
    def setUpClass(cls):
        node_info = {}
        fake_config = fixtures.FakeConfig()
        node_info = fake_config.get_node_info()

        with open(cls.TMP_CONF_FILE, "w") as f:
            yaml.dump(node_info, f, default_flow_style=False)

        node = CNode(node_info)
        node.init()
        node.precheck()
        node.start()

        # Wait ipmi_sim sever coming up.
        # FIXME: good way???
        print "Wait ipmi-console start in about 30s..."
        time.sleep(15)

        ipmi_console_thread = threading.Thread(target=console.start, args=(node_info["name"],))
        ipmi_console_thread.setDaemon(True)
        ipmi_console_thread.start()

        # Wait SSH server coming up
        # FIXME: Need a good way to check if SSH server is listening
        # on port 9300
        time.sleep(20)
        cls.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cls.ssh.connect('127.0.0.1', username='', password='', port=9300)
        cls.channel = cls.ssh.invoke_shell()

    @classmethod
    def tearDownClass(cls):
        cls.channel.send('quit\n')
        cls.channel.close()
        cls.ssh.close()

        with open(cls.TMP_CONF_FILE, "r") as yml_file:
            node_info = yaml.load(yml_file)

        console.stop(node_info["name"])

        node = CNode(node_info)
        node.init()
        node.stop()

        if os.path.exists(cls.TMP_CONF_FILE):
            os.unlink(cls.TMP_CONF_FILE)

        workspace = os.path.join(config.infrasim_home, "test")
        if os.path.exists(workspace):
            shutil.rmtree(workspace)


    def test_sensor_accessibility(self):
        self.channel.send('sensor info\n')
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert 'degrees C' in str_output

        self.channel.send('sensor value get ' + self.sensor_id + '\n')
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert 'Fan_SYS0' in str_output

        self.channel.send('sensor value set ' + self.sensor_id + ' ' + self.sensor_value + '\n')
        time.sleep(1)

        self.channel.send('sensor value get ' + self.sensor_id + '\n')
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert 'Fan_SYS0 : 1000.000 RPM' in str_output

    def test_help_accessibility(self):
        self.channel.send('help\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        assert 'Available' in str_output

    def test_sel_accessibility(self):
        ipmi_sel_cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin sel clear'
        run_command(ipmi_sel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.channel.send('sel get ' + self.sensor_id + '\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        assert 'ID' in str_output

        self.channel.send('sel set ' + self.sensor_id + ' ' + self.event_id + ' assert\n')
        time.sleep(0.1)
        self.channel.send('sel set ' + self.sensor_id + ' ' + self.event_id + ' deassert\n')
        time.sleep(2)

        ipmi_sel_cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin sel list'
        returncode, output = run_command(ipmi_sel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            lines = str(output).splitlines()
            assert_line = lines[-2]
            deassert_line = lines[-1]
        except IndexError:
            assert False

        assert 'Fan #0xc0 | Upper Non-critical going low  | Asserted' in assert_line
        assert 'Fan #0xc0 | Upper Non-critical going low  | Deasserted' in deassert_line

    def test_history_accessibilty(self):
        self.channel.send('help\n')
        time.sleep(0.1)
        self.channel.send('help sensor\n')
        time.sleep(0.1)
        self.channel.send('history\n')
        time.sleep(0.1)

        str_output = read_buffer(self.channel)
        lines = str_output.splitlines()

        assert 'help' in lines[-4]
        assert 'help sensor' in lines[-3]

    def test_sensor_value_get_discrete(self):
        reset_console(self.channel)

        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        self.assertTrue("PSU1 Status : 0x0100" in str_output)
        time.sleep(1)

    def test_sensor_value_set_discrete(self):
        self.channel.send("sensor value set 0xe0 0xca01\n")
        time.sleep(3)
        read_buffer(self.channel)

        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        self.assertTrue("PSU1 Status : 0xca01" in str_output)

        self.channel.send("sensor value set 0xe0 0x0100\n")
        time.sleep(3)
        read_buffer(self.channel)

    def test_sensor_value_set_discrete_invalid_length(self):
        reset_console(self.channel)

        self.channel.send("sensor value set 0xe0 0xca100\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)

        self.assertTrue("Available 'sensor value' commands:" in str_output)

        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        self.assertTrue("PSU1 Status : 0x0100" in str_output)

    def test_sensor_value_set_discrete_invalid_value(self):
        reset_console(self.channel)

        self.channel.send("sensor value set 0xe0 abc\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        self.assertTrue("Available 'sensor value' commands:" in str_output)

        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        self.assertTrue("PSU1 Status : 0x0100" in str_output)

    def test_sensor_value_set_discrete_state(self):
        reset_console(self.channel)

        self.channel.send("sensor value set 0xe0 state 12 1\n")
        time.sleep(0.1)
        read_buffer(self.channel)
        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        self.assertTrue("PSU1 Status : 0x0110" in str_output)

        self.channel.send("sensor value set 0xe0 0x0100\n")
        time.sleep(0.1)
        read_buffer(self.channel)

    def test_sensor_value_set_discrete_state_invalid_bit(self):
        reset_console(self.channel)

        self.channel.send("sensor value set 0xe0 state 15 1\n")
        time.sleep(0.1)
        read_buffer(self.channel)
        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)

        self.assertTrue("PSU1 Status : 0x0100" in str_output)

    def test_sensor_value_set_discrete_state_invalid_value(self):
        reset_console(self.channel)

        self.channel.send("sensor value set 0xe0 state 12 2\n")
        time.sleep(0.1)
        read_buffer(self.channel)
        self.channel.send("sensor value get 0xe0\n")
        time.sleep(0.1)
        str_output = read_buffer(self.channel)

        self.assertTrue("PSU1 Status : 0x0100" in str_output)


class test_ipmi_console_config_change(unittest.TestCase):

    ssh = paramiko.SSHClient()
    channel = None
    # Just for quanta_d51
    sensor_id = '0xc0'
    sensor_value = '1000.00'
    event_id = '6'
    TMP_CONF_FILE = "/tmp/test.yml"
    bmc_conf = ""

    @classmethod
    def setUpClass(cls):
        node_info = {}
        fake_config = fixtures.FakeConfig()
        node_info = fake_config.get_node_info()
        node_info["ipmi_console_port"] = 9100
        node_info["ipmi_console_ssh"] = 9400
        cls.bmc_conf = os.path.join(os.environ["HOME"], ".infrasim",
                                    node_info["name"], "etc", "vbmc.conf")

        with open(cls.TMP_CONF_FILE, "w") as f:
            yaml.dump(node_info, f, default_flow_style=False)

        node = CNode(node_info)
        node.init()
        node.precheck()
        node.start()

        # Wait ipmi_sim sever coming up.
        # FIXME: good way???
        print "Wait ipmi-console start in about 30s..."
        time.sleep(15)

        ipmi_console_thread = threading.Thread(target=console.start, args=(node_info["name"],))
        ipmi_console_thread.setDaemon(True)
        ipmi_console_thread.start()

        # console.start(node_info["name"])

        # Wait SSH server coming up
        # FIXME: Need a good way to check if SSH server is listening
        # on port 9300
        time.sleep(20)

    @classmethod
    def tearDownClass(cls):

        with open(cls.TMP_CONF_FILE, "r") as yml_file:
            node_info = yaml.load(yml_file)

        console.stop(node_info["name"])

        node = CNode(node_info)
        node.init()
        node.stop()

        if os.path.exists(cls.TMP_CONF_FILE):
            os.unlink(cls.TMP_CONF_FILE)

        workspace = os.path.join(config.infrasim_home, "test")
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    def test_ipmi_console_valid_port(self):
        """
        Verify vBMC console is listening on port 9100
        """
        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()
        assert 'console 0.0.0.0 9100' in bmc_conf

        tn = telnetlib.Telnet(host="127.0.0.1", port=9100, timeout=5)
        tn.read_until(">")
        tn.write("get_user_password 0x20 admin\n")
        tn.read_until("\nadmin", timeout=5)
        tn.close()

    def test_ipmi_console_invalid_port(self):
        """
        Verify vBMC console is not listening on default port 9000
        """
        try:
            tn = telnetlib.Telnet(host="127.0.0.1", port=9000, timeout=5)
        except socket.error:
            pass
        else:
            raise self.fail("Default port 9000 for ipmi-console is still "
                            "in use after changed to 9100.")

    def test_ipmi_console_valid_ssh(self):
        """
        Verify port 9400 is valid
        """
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1', username='', password='', port=9400)
        channel = self.ssh.invoke_shell()

        try:
            channel.send("\n")
            time.sleep(0.1)
            str_output = read_buffer(channel)
            self.assertTrue("IPMI_SIM>" in str_output)
        except:
            channel.send("quit\n")
            channel.close()
            self.ssh.close()
            raise
        else:
            channel.send("quit\n")
            channel.close()
            self.ssh.close()

    def test_ipmi_console_invalid_ssh(self):
        """
        Verify default port 9300 is invalid now
        """
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect('127.0.0.1', username='', password='', port=9300)
        except socket.error:
            pass
        else:
            self.fail("Expect server refuse connection to port 9300, "
                      "but test fail")
