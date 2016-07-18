#!/usr/bin/env python 
# -*- coding: utf-8 -*-


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


def setup_func():
    socat.start_socat()
    ipmi.start_ipmi('quanta_d51')
    run_command('ipmi-console start &', True, None, None)
    time.sleep(3)
    

def teardown_func():
    run_command('ipmi-console stop', True, None, None)
    qemu.stop_qemu()
    ipmi.stop_ipmi()
    socat.stop_socat()


@with_setup(setup_func, teardown_func)
def test_sensor_accessibility():
    # Just for quanta_d51
    sensor_id = '0xc0'
    sensor_value = '1000.00'

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('127.0.0.1', username='', password='', port=9300)

    channel = ssh.invoke_shell()

    channel.send('sensor info\n')
    channel.send('\n')
    time.sleep(0.1)
    str_output = read_buffer(channel)
    print str_output
    assert str_output.find('degrees C') != -1

    channel.send('sensor value get ' + sensor_id + '\n')
    channel.send('\n')
    time.sleep(0.1)
    str_output = read_buffer(channel)
    print str_output
    assert str_output.find('Fan_SYS0') != -1

    channel.send('sensor value set ' + sensor_id + ' ' + sensor_value + '\n')
    time.sleep(0.1)

    channel.send('sensor value get ' + sensor_id + '\n')
    channel.send('\n')
    time.sleep(0.1)
    str_output = read_buffer(channel)
    print str_output
    assert str_output.find('Fan_SYS0 : 1000.000 RPM') != -1

    channel.close()
    ssh.close()


@with_setup(setup_func, teardown_func)
def test_help_accessibility():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('127.0.0.1', username='', password='', port=9300)

    channel = ssh.invoke_shell()

    channel.send('help\n')
    channel.send('\n')
    time.sleep(0.1)
    str_output = read_buffer(channel)
    assert str_output.find('Available') != -1

    channel.close()
    ssh.close()


@with_setup(setup_func, teardown_func)
def test_sel_accessibility():
    # Just for quanta_d51
    sensor_id = '0xc0'
    event_id = '6'

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('127.0.0.1', username='', password='', port=9300)

    channel = ssh.invoke_shell()

    channel.send('sel get ' + sensor_id + '\n')        
    channel.send('\n')
    time.sleep(0.1)
    str_output = read_buffer(channel)
    assert str_output.find('ID') != -1

    channel.send('sel set ' + sensor_id + ' ' + event_id + ' assert\n')
    channel.send('\n')
    time.sleep(0.1)
    channel.send('sel set ' + sensor_id + ' ' + event_id + ' deassert\n')
    channel.send('\n')
    time.sleep(0.1)

    ipmi_sel_cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin sel list'
    returncode, output = run_command(ipmi_sel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print output
    assert returncode == 0

    channel.close()


@with_setup(setup_func, teardown_func)
def test_history_accessibilty():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('127.0.0.1', username='', password='', port=9300)

    channel = ssh.invoke_shell()

    channel.send('help\n')        
    channel.send('\n')
    time.sleep(0.1)
    channel.send('help sensor\n')        
    channel.send('\n')
    time.sleep(0.1)
    channel.send('history\n')        
    time.sleep(0.1)

    str_output = read_buffer(channel)
    lines = str_output.splitlines()
    print lines

    assert lines[-4] == '0  help'
    assert lines[-3] == '1  help sensor'

    channel.close()
    ssh.close()



