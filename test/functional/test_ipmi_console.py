#!/usr/bin/env python 
# -*- coding: utf-8 -*-


import unittest
import subprocess
import re
import os
import time
import paramiko
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from nose import with_setup


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
        str_read = str(channel.recv(4096))
        str_output += str_read
        if str_read.find('IPMI_SIM>\n'):
            break
        time.sleep(0.1)
    return str_output


class test_ipmi_console(unittest.TestCase):

    ssh = paramiko.SSHClient()
    channel = None
    # Just for quanta_d51
    sensor_id = '0xc0'
    sensor_value = '1000.00'
    event_id = '6'

    @classmethod
    def setUpClass(cls):
        socat.start_socat()
        ipmi.start_ipmi('quanta_d51')
        run_command('ipmi-console start &', True, None, None)
        time.sleep(5)
        cls.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cls.ssh.connect('127.0.0.1', username='', password='', port=9300)
        cls.channel = cls.ssh.invoke_shell()
    
    @classmethod
    def tearDownClass(cls):
        cls.channel.close()
        cls.ssh.close()
        run_command('ipmi-console stop', True, None, None)
        qemu.stop_qemu()
        ipmi.stop_ipmi()
        socat.stop_socat()


    def test_sensor_accessibility(self):
        self.channel.send('sensor info\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        print str_output
        assert str_output.find('degrees C') != -1
    
        self.channel.send('sensor value get ' + self.sensor_id + '\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        print str_output
        assert str_output.find('Fan_SYS0') != -1
    
        self.channel.send('sensor value set ' + self.sensor_id + ' ' + self.sensor_value + '\n')
        time.sleep(0.1)
    
        self.channel.send('sensor value get ' + self.sensor_id + '\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        print str_output
        assert str_output.find('Fan_SYS0 : 1000.000 RPM') != -1
    
    
    def test_help_accessibility(self):
        self.channel.send('help\n')
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        assert str_output.find('Available') != -1
    
    
    def test_sel_accessibility(self):
        self.channel.send('sel get ' + self.sensor_id + '\n')        
        time.sleep(0.1)
        str_output = read_buffer(self.channel)
        assert str_output.find('ID') != -1
    
        self.channel.send('sel set ' + self.sensor_id + ' ' + self.event_id + ' assert\n')
        time.sleep(0.1)
        self.channel.send('sel set ' + self.sensor_id + ' ' + self.event_id + ' deassert\n')
        time.sleep(0.1)
    
        ipmi_sel_cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin sel list'
        returncode, output = run_command(ipmi_sel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lines = str(output).splitlines()
        assert_line = lines[-2]
        deassert_line = lines[-1]
        print assert_line
        print deassert_line
        assert assert_line.find('Fan #0xc0 | Upper Non-critical going low  | Asserted') != -1
        assert deassert_line.find('Fan #0xc0 | Upper Non-critical going low  | Deasserted') != -1
    
    
    def test_history_accessibilty(self):
        self.channel.send('help\n')        
        time.sleep(0.1)
        self.channel.send('help sensor\n')        
        time.sleep(0.1)
        self.channel.send('history\n')        
        time.sleep(0.1)
    
        str_output = read_buffer(self.channel)
        lines = str_output.splitlines()
        print str_output
    
        assert lines[-4].find('help') != -1
        assert lines[-3].find('help sensor') != -1




