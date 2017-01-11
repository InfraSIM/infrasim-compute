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
import yaml
import time
import hashlib
import paramiko
from infrasim import model
from infrasim import helper
from infrasim import InfraSimError
from test import fixtures

PS_QEMU = "ps ax | grep qemu"
PS_IPMI = "ps ax | grep ipmi"
PS_SOCAT = "ps ax | grep socat"
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


class test_compute_configuration_change(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        # if os.path.exists(TMP_CONF_FILE):
        #    os.unlink(TMP_CONF_FILE)

    def test_set_vcpu(self):
        self.conf["compute"]["cpu"]["quantities"] = 8
        # with open(TMP_CONF_FILE, "w") as yaml_file:
        #    yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-smp 8" in str_result

    def test_set_cpu_family(self):
        self.conf["compute"]["cpu"]["type"] = "IvyBridge"
        # with open(TMP_CONF_FILE, "w") as yaml_file:
        #    yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-cpu IvyBridge" in str_result

    def test_set_memory_capacity(self):
        self.conf["compute"]["memory"]["size"] = 1536
        with open(TMP_CONF_FILE, "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-m 1536" in str_result

    def test_set_disk_drive(self):
        self.conf["compute"]["storage_backend"] = [{
            "controller": {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8}, {"size": 8}]
            }
        }]
        # with open(TMP_CONF_FILE, "w") as yaml_file:
        #    yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert ".infrasim/sda.img,format=qcow2" in str_result
        assert ".infrasim/sdb.img,format=qcow2" in str_result

    def test_qemu_boot_from_disk_img(self):
        MD5_CIRROS_IMG = "ee1eca47dc88f4879d8a229cc70a07c6"
        DOWNLOAD_URL = "http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img"
        test_img_file = "/tmp/cirros-0.3.4-x86_64-disk.img"
        try:
            helper.fetch_image(DOWNLOAD_URL, MD5_CIRROS_IMG, test_img_file)
        except InfraSimError, e:
            print e.value
            assert False


        self.conf["compute"]["storage_backend"] = [{
            "controller": {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8, "file": test_img_file}]
            }
        }]
        # with open(TMP_CONF_FILE, "w") as yaml_file:
        #    yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        import telnetlib
        import paramiko
        import time
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
                ssh.connect("127.0.0.1", port=2222, username="cirros",
                            password="cubswin:)", timeout=120)
                ssh.close()
                break
            except paramiko.SSHException:
                time.sleep(1)
                continue
            except Exception:
                assert False
                return

        assert True


class test_bmc_configuration_change(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        # if os.path.exists(TMP_CONF_FILE):
        #    os.unlink(TMP_CONF_FILE)
        self.conf = None

    def test_set_bmc_iol_port(self):
        self.conf["bmc"] = {}
        self.conf["bmc"]["ipmi_over_lan_port"] = 624

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin -p 624 -I lanplus ' \
              'raw 0x06 0x01'
        returncode, output = run_command(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        assert returncode == 0

        cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin -p 623 -I lanplus ' \
              'raw 0x06 0x01'
        returncode, output = run_command(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        assert returncode != 0

    def test_set_bmc_interface(self):
        """
        Set BMC listen on specified interface and won't response to another
        :return:
        """
        # Find two valid interface with IP in to a list, e.g:
        # [{"interface":"ens160","ip":"192.168.190.9"}, {}]
        # If the list has no less than 2 interface, do this test
        valid_nic = []
        for interface in helper.get_all_interfaces():
            ip = helper.get_interface_ip(interface)
            if ip:
                valid_nic.append({"interface": interface, "ip": ip})

        if len(valid_nic) < 2:
            raise self.skipTest("No enough nic for test")

        # Set BMC to listen on first valid nic
        # Try to access via first one, it works
        # Try to access via second one, it fails
        self.conf["bmc"] = {}
        self.conf["bmc"]["interface"] = valid_nic[0]["interface"]

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        cmd = 'ipmitool -H {} -U admin -P admin -I lanplus raw 0x06 0x01'.\
            format(valid_nic[0]["ip"])
        ret, rsp = run_command(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        assert ret == 0

        cmd = 'ipmitool -H {} -U admin -P admin -I lanplus raw 0x06 0x01'.\
            format(valid_nic[1]["ip"])
        ret, rsp = run_command(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        assert ret != 0


class test_connection(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()
        self.bmc_conf = os.path.join(os.environ["HOME"], ".infrasim",
                                     "test", "etc", "vbmc.conf")
        self.old_path = os.environ.get("PATH")
        os.environ["PATH"] = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), self.old_path)

    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        if os.path.exists(TMP_CONF_FILE):
            os.unlink(TMP_CONF_FILE)
        self.conf = None
        os.environ["PATH"] = self.old_path

    def test_set_sol_device(self):
        temp_sol_device = "{}/.infrasim/pty_test".format(os.environ['HOME'])
        self.conf["sol_device"] = temp_sol_device
        self.conf["sol_enable"] = True

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_SOCAT, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "pty,link={},waitslave".format(temp_sol_device) in str_result

        with open(self.bmc_conf, "r") as fp:
            fake_bmc_conf = fp.read()
        assert 'sol "{}" 115200'.format(temp_sol_device) in fake_bmc_conf

    def test_set_ipmi_console_port(self):
        self.conf["ipmi_console_port"] = 9100

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()
        assert 'console 0.0.0.0 9100' in bmc_conf

        print '\033[93m{}\033[0m'.\
            format("Not implemented: "
                   "test if ipmi-console connect to same port")

    def test_set_bmc_connection_port(self):
        self.conf["bmc_connection_port"] = 9102

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        with open(self.bmc_conf, "r") as fp:
            bmc_conf = fp.read()
        assert 'serial 15 0.0.0.0 9102 codec VM ipmb 0x20' in bmc_conf

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "port=9102" in str_result

    def test_set_serial_port(self):
        self.conf["sol"] = True
        self.conf["serial_port"] = 9103

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "-chardev udp,host=127.0.0.1,port=9103,id=serial0,reconnect=10" in str_result
        assert "-device isa-serial,chardev=serial0" in str_result

        str_result = run_command(PS_SOCAT, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "udp-listen:9103,reuseaddr,fork" in str_result

    def test_set_node_type(self):
        self.conf["type"] = "dell_c6320"

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "qemu-system-x86_64" in str_result
        assert "-smbios file={}/.infrasim/test/data/dell_c6320_smbios.bin".\
            format(os.environ["HOME"]) in str_result

        str_result = run_command(PS_IPMI, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "-f {}/.infrasim/test/data/dell_c6320.emu".\
            format(os.environ["HOME"]) in str_result


class test_racadm_configuration_change(unittest.TestCase):

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

    def test_default_config(self):
        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check process
        str_result = run_command(PS_RACADM, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "racadmsim test 0.0.0.0 10022 admin admin" in str_result

        # Prepare SSH channel
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10022)
        self.channel = self.ssh.invoke_shell()

        # Test 1
        self.channel.send("help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "racadm" in str_output

        # Test 2
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_set_credential(self):
        self.conf["racadm"] = {}
        self.conf["racadm"]["username"] = "admin"
        self.conf["racadm"]["password"] = "fake"

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check process
        str_result = run_command(PS_RACADM, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "racadmsim test 0.0.0.0 10022 admin fake" in str_result

        # Connect with wrong credential
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect('127.0.0.1',
                             username='admin',
                             password='admin',
                             port=10022)
        except paramiko.AuthenticationException:
            assert True
        else:
            assert False

        # Connect with correct credential
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='fake',
                         port=10022)
        self.channel = self.ssh.invoke_shell()

        # Test racadmsim is working
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_set_port(self):
        self.conf["racadm"] = {}
        self.conf["racadm"]["port"] = 10023

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check process
        str_result = run_command(PS_RACADM, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "racadmsim test 0.0.0.0 10023 admin admin" in str_result

        # Connect with wrong port
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect('127.0.0.1',
                             username='admin',
                             password='admin',
                             port=10022)
        except paramiko.ssh_exception.NoValidConnectionsError:
            assert True
        else:
            assert False

        # Connect with correct port
        self.ssh.connect('127.0.0.1',
                         username='admin',
                         password='admin',
                         port=10023)
        self.channel = self.ssh.invoke_shell()

        # Test racadmsim is working
        self.channel.send("racadm help"+chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "hwinventory" in str_output

    def test_command_in_line(self):

        str_result = run_command("which sshpass", True,
                                 subprocess.PIPE, subprocess.PIPE)
        if str_result[0] != 0:
            self.skipTest("Need sshpass to test inline ssh command")

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Test help in iDrac console
        cmd_help = "sshpass -p 'admin' " \
                   "ssh admin@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "help"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert "racadm" in cmd_result[0]

        # Test help in racadm console
        cmd_help = "sshpass -p 'admin' " \
                   "ssh admin@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "racadm help"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert "hwinventory" in cmd_result[0]

        # Test wrong username fail
        cmd_help = "sshpass -p 'admin' " \
                   "ssh fake@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "racadm help"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert "Permission denied" in cmd_result[1]

        # Test wrong password fail
        cmd_help = "sshpass -p 'fake' " \
                   "ssh admin@127.0.0.1 " \
                   "-p 10022 " \
                   "-o StrictHostKeyChecking=no " \
                   "racadm help"
        child = subprocess.Popen(cmd_help, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        cmd_result = child.communicate()
        assert "Permission denied" in cmd_result[1]
