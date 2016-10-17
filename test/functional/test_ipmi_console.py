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
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import console
from infrasim import config
import threading
import yaml


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


class test_ipmi_console(unittest.TestCase):

    ssh = paramiko.SSHClient()
    channel = None
    # Just for quanta_d51
    sensor_id = '0xc0'
    sensor_value = '1000.00'
    event_id = '6'

    @classmethod
    def setUpClass(cls):
        node_info = {}
        with open(config.infrasim_initial_config, 'r') as f_yml:
            node_info = yaml.load(f_yml)
        node_info["name"] = "test"

        with open("/tmp/test.yaml", "w") as f:
            yaml.dump(node_info, f, default_flow_style=False)

        socat.start_socat(conf_file="/tmp/test.yaml")
        ipmi.start_ipmi(conf_file="/tmp/test.yaml")
        # Wait ipmi_sim sever coming up.
        # FIXME: good way???
        time.sleep(5)
        ipmi_console_thread = threading.Thread(target=console.start, args=())
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
        qemu.stop_qemu(conf_file="/tmp/test.yaml")
        ipmi.stop_ipmi(conf_file="/tmp/test.yaml")
        socat.stop_socat(conf_file="/tmp/test.yaml")
        os.system("rm -rf {}/.infrasim/test/".format(os.environ["HOME"]))

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
        self.channel.send('sel get ' + self.sensor_id + '\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        assert 'ID' in str_output

        self.channel.send('sel set ' + self.sensor_id + ' ' + self.event_id + ' assert\n')
        time.sleep(0.1)
        self.channel.send('sel set ' + self.sensor_id + ' ' + self.event_id + ' deassert\n')
        time.sleep(0.1)

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
