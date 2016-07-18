#!/usr/bin/env python 
# -*- coding: utf-8 -*-


import unittest
import subprocess
import re
import os
import time
import paramiko
from threading import Lock
from threading import Thread
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat


def run_command(cmd="", shell=True, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


class TestIpmiConsole(unittest.TestCase):
    
    ssh = paramiko.SSHClient()
    lock_buffer = Lock()
    lock_connection = Lock()

    @classmethod
    def setUpClass(cls):
        socat.start_socat()
        time.sleep(3)
        ipmi.start_ipmi('quanta_d51')
        time.sleep(3)
        run_command('ipmi-console start &', True, None, None)
        time.sleep(10)
    
    @classmethod
    def tearDownClass(cls):
        run_command('ipmi-console stop', True, None, None)
        time.sleep(3)
        ipmi.stop_ipmi()
        socat.stop_socat()

    def flush_buffer(self):
        self.lock_buffer.acquire()
        self.lock_buffer.release()

    def read_buffer(self, channel):
        while not channel.recv_ready():
            continue
        str_output = ''
        str_read = ''
        while True:
            str_read = str(channel.recv(4096))
            str_output += str_read
            if str_read.find('IPMI_SIM>\n'):
                break
            self.flush_buffer()
            time.sleep(0.1)
        return str_output

    def test_sensor_accessibility(self):
        # Just for quanta_d51
        sensor_id = '0xc0'
        sensor_value = '1000.00'

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('127.0.0.1', username='', password='', port=9300)
        time.sleep(3)
        channel = ssh.invoke_shell()

        channel.send('sensor info\n')
        channel.send('\n')
        time.sleep(0.1)
        str_output = self.read_buffer(channel)
        self.assertNotEqual(str_output.find('degrees C'), -1)

        channel.send('sensor value get ' + sensor_id + '\n')
        channel.send('\n')
        time.sleep(0.1)
        str_output = self.read_buffer(channel)
        self.assertNotEqual(str_output.find('Fan_SYS0'), -1)

        channel.send('sensor value set ' + sensor_id + ' ' + sensor_value + '\n')
        time.sleep(0.1)

        channel.send('sensor value get ' + sensor_id + '\n')
        channel.send('\n')
        time.sleep(0.1)
        str_output = self.read_buffer(channel)
        self.assertNotEqual(str_output.find('Fan_SYS0 : 1000.000 RPM'), -1)

        channel.close()
        ssh.close()

    def test_help_accessibility(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('127.0.0.1', username='', password='', port=9300)
        time.sleep(3)
        channel = ssh.invoke_shell()

        channel.send('help\n')
        channel.send('\n')
        time.sleep(0.1)
        str_output = self.read_buffer(channel)
        self.assertNotEqual(str_output.find('Available'), -1)

        channel.close()
        ssh.close()

        


