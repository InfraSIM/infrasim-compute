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
from infrasim import model
from test import fixtures

PS_RACADM = "ps ax | grep racadmsim"

TMP_CONF_FILE = "/tmp/test.yml"


def run_command(cmd="", shell=True, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell,
                             stdout=stdout, stderr=stderr)
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
        if str_output.find('/admin1-> \n'):
            break
        time.sleep(1)
    return str_output


class test_racadm_robust(unittest.TestCase):

    ssh = paramiko.SSHClient()
    channel = None

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()
        self.conf["type"] = "dell_c6320"
        self.old_path = os.environ.get("PATH")
        os.environ["PATH"] = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), self.old_path)

    def tearDown(self):
        if self.channel:
            self.channel.send('quit\n')
            self.channel.close()
        self.ssh.close()

        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        if os.path.exists(TMP_CONF_FILE):
            os.unlink(TMP_CONF_FILE)
        self.conf = None
        os.environ["PATH"] = self.old_path

    def test_server_live_after_inline_wrong_password(self):

        str_result = run_command("which sshpass", True,
                                 subprocess.PIPE, subprocess.PIPE)
        if str_result[0] != 0:
            self.skipTest("Need sshpass to test inline ssh command")

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Use wrong credential
        cmd_help = "sshpass -p 'fake' " \
                   "ssh admin@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "help"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert "Permission denied" in cmd_result[1]

        # Verify server is alive
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10022)
        self.channel = self.ssh.invoke_shell()
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_server_live_after_inline_wrong_username(self):

        str_result = run_command("which sshpass", True,
                                 subprocess.PIPE, subprocess.PIPE)
        if str_result[0] != 0:
            self.skipTest("Need sshpass to test inline ssh command")

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Use wrong credential
        cmd_help = "sshpass -p 'admin' " \
                   "ssh fake@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "help"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert "Permission denied" in cmd_result[1]

        # Verify server is alive
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10022)
        self.channel = self.ssh.invoke_shell()
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_server_live_after_inline_wrong_command(self):

        str_result = run_command("which sshpass", True,
                                 subprocess.PIPE, subprocess.PIPE)
        if str_result[0] != 0:
            self.skipTest("Need sshpass to test inline ssh command")

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Use wrong credential
        cmd_help = "sshpass -p 'admin' " \
                   "ssh admin@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "fake"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert 'Unknown command, run "help" for detail' in cmd_result[0]

        # Verify server is alive
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10022)
        self.channel = self.ssh.invoke_shell()
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_server_live_after_inline_wrong_racadm_command(self):

        str_result = run_command("which sshpass", True,
                                 subprocess.PIPE, subprocess.PIPE)
        if str_result[0] != 0:
            self.skipTest("Need sshpass to test inline ssh command")

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Use wrong credential
        cmd_help = "sshpass -p 'admin' " \
                   "ssh admin@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "racadm fake"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert 'Unknown command, run "help" for detail' in cmd_result[0]

        # Verify server is alive
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10022)
        self.channel = self.ssh.invoke_shell()
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_login_and_exit_racadm_repl(self):
        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Prepare SSH channel
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10022)
        self.channel = self.ssh.invoke_shell()

        # Go to iDRAC console
        self.channel.send("help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "racadm" in str_output

        # Go to racadm console
        self.channel.send("racadm"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "Welcome to RacadmConsole" in str_output

        self.channel.send(chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "racadmsim>>" in str_output

        # Exit racadm console
        self.channel.send("exit"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "Exit RacadmConsole console" in str_output

        self.channel.send(chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "/admin1->" in str_output
