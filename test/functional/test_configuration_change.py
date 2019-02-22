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
import paramiko
import re
from infrasim import workspace
import json
import requests
from infrasim import model
from infrasim import helper
from infrasim.helper import UnixSocket
from test import fixtures
from infrasim import config

PS_QEMU = "ps ax | grep qemu"
PS_IPMI = "ps ax | grep ipmi"
PS_SOCAT = "ps ax | grep socat"
PS_RACADM = "ps ax | grep racadmsim"
PS_MONITOR = "ps ax | grep monitor"

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


def get_qemu_pid(node):
    for t in node.get_task_list():
        if isinstance(t, model.CCompute):
            return t.get_task_pid()
    return None


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
        drive_files = ["/tmp/sda.img", "/tmp/sdb.img"]
        for drive_file in drive_files:
            if os.path.exists(drive_file):
                os.unlink(drive_file)

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
        str_result = helper.get_full_qemu_cmd(str_result)

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
        str_result = helper.get_full_qemu_cmd(str_result)

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
        str_result = helper.get_full_qemu_cmd(str_result)

        assert "qemu-system-x86_64" in str_result
        assert "-m 1536" in str_result

    def test_set_disk_drive(self):
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [
                {"size": 8, "file": "/tmp/sda.img"},
                {"size": 8, "file": "/tmp/sdb.img"}
            ]
        }]
        # with open(TMP_CONF_FILE, "w") as yaml_file:
        #    yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")
        qemu_cmdline = helper.get_full_qemu_cmd(qemu_cmdline)

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline

    def test_qemu_boot_from_disk_img(self):

        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [{"size": 8, "file": fixtures.image}]
        }]
        # with open(TMP_CONF_FILE, "w") as yaml_file:
        #    yaml.dump(self.conf, yaml_file, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Port forward from guest 22 to host 2222
        path = os.path.join(node.workspace.get_workspace(), ".monitor")
        s = UnixSocket(path)
        s.connect()
        s.recv()

        payload_enable_qmp = {
            "execute": "qmp_capabilities"
        }

        s.send(json.dumps(payload_enable_qmp))
        s.recv()

        payload_port_forward = {
            "execute": "human-monitor-command",
            "arguments": {
                "command-line": "hostfwd_add ::2222-:22"
            }
        }
        s.send(json.dumps(payload_port_forward))
        s.recv()
        s.close()

        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("filename.log")
        helper.try_func(600, paramiko.SSHClient.connect, ssh,
                        "127.0.0.1", port=2222, username="root",
                        password="root", timeout=120)
        ssh.close()

    @helper.qemu_version(">=2.10")
    def test_auto_add_nvme_serial(self):
        self.conf["compute"]["storage_backend"] = [{
            "type": "nvme",
            "cmb_size": 256,
            "size": 8
        }]

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check process option has nvme serial
        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        str_result = helper.get_full_qemu_cmd(str_result)
        p = re.compile(r"-device nvme.*serial=(\w+)")
        m = p.search(str_result)
        assert m is not None

        # Check config in workspace has nvme serial
        node_info = workspace.Workspace.get_node_info_in_workspace(self.conf["name"])
        serial = node_info["compute"]["storage_backend"][0]["serial"]
        assert m.group(1) == serial


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

    def test_set_bmc_lan_channel(self):
        self.conf["bmc"] = {}
        self.conf["bmc"]["main_channel"] = 3

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # FIXME: ipmi_sim takes time to set lan configuration through lancontrol script.
        time.sleep(2)

        cmd = 'ipmitool -H 127.0.0.1 -U admin -P admin -I lanplus lan print {}'

        assert run_command(cmd.format(self.conf["bmc"]["main_channel"]),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)[0] == 0

        assert run_command(cmd.format(1),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)[0] != 0

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
        self.bmc_conf = os.path.join(config.infrasim_home, "test", "etc", "vbmc.conf")
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
        temp_sol_device = os.path.join(config.infrasim_home, "pty_test")
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
        assert 'serial kcs 0.0.0.0 9102 codec VM ipmb 0x20' in bmc_conf

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        str_result = helper.get_full_qemu_cmd(str_result)
        assert "port=9102" in str_result

    def test_set_serial_socket(self):
        self.conf["sol_enable"] = True
        self.conf["serial_socket"] = "/tmp/test_infrasim_set_serial_socket"

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        str_result = helper.get_full_qemu_cmd(str_result)
        assert "-chardev socket,path=/tmp/test_infrasim_set_serial_socket," \
               "id=serial0,nowait,reconnect=10" in str_result
        assert "-device isa-serial,chardev=serial0" in str_result

        str_result = run_command(PS_SOCAT, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "unix-listen:/tmp/test_infrasim_set_serial_socket," \
               "fork" in str_result

    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def test_set_node_type(self):
        self.conf["type"] = "dell_c6320"

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        str_result = run_command(PS_QEMU, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        str_result = helper.get_full_qemu_cmd(str_result)
        assert "qemu-system-x86_64" in str_result
        assert "-smbios file={}/test/data/dell_c6320_smbios.bin".\
            format(config.infrasim_home) in str_result

        str_result = run_command(PS_IPMI, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "-f {}/test/data/dell_c6320.emu".\
            format(config.infrasim_home) in str_result


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
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
        self.channel.send("help" + chr(13))
        time.sleep(1)
        str_output = read_buffer(self.channel)
        assert "racadm" in str_output

        # Test 2
        self.channel.send("racadm help" + chr(13))
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
        self.channel.send("racadm help" + chr(13))
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
        self.channel.send("racadm help" + chr(13))
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


class test_infrasim_monitor_configuration_change(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()
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

    def wait_port_up(self, addr, port, timeout=10):
        start = time.time()
        while True:
            if helper.check_if_port_in_use(addr, port):
                return True

            if time.time() - start > timeout:
                break

            time.sleep(0.1)

        return False

    def test_default_config(self):
        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        assert self.wait_port_up("0.0.0.0", 9005)

        # Check process
        str_result = run_command(PS_MONITOR, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "infrasim-monitor test 0.0.0.0 9005" in str_result

        # Verify connection
        rsp = requests.get("http://localhost:9005/admin")
        assert rsp.status_code == 200

    def test_set_port(self):
        self.conf["monitor"] = {
            "enable": True,
            "port": 9006
        }

        # Start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check process
        str_result = run_command(PS_MONITOR, True,
                                 subprocess.PIPE, subprocess.PIPE)[1]
        assert "infrasim-monitor test 0.0.0.0 9006" in str_result

        # Connect with wrong port
        try:
            rsp = requests.get("http://localhost:9005/admin")
        except requests.exceptions.ConnectionError:
            pass
        else:
            assert False

        assert self.wait_port_up("0.0.0.0", 9006)

        # Connect with correct port
        rsp = requests.get("http://localhost:9006/admin")
        assert rsp.status_code == 200

    def test_set_interface(self):
        # Find two valid interface with IP in to a list, e.g:
        # [{"interface":"ens160","ip":"192.168.190.9"}, {}]
        # If the list has no less than 2 interface, do this test
        valid_nic = []
        for interface in helper.get_all_interfaces():
            ip = helper.get_interface_ip(interface)
            if ip and (interface.startswith("en") or interface.startswith("eth") or
                       interface.startswith("br")):
                valid_nic.append({"interface": interface, "ip": ip})

        if len(valid_nic) < 2:
            raise self.skipTest("No enough nic for test")

        print valid_nic

        # Set BMC to listen on first valid nic
        # Try to access via first one, it works
        # Try to access via second one, it fails
        self.conf["monitor"] = {
            "enable": True,
            "interface": valid_nic[0]["interface"]
        }
        print self.conf["monitor"]

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check if port is opened
        start = time.time()
        while helper.check_if_port_in_use(valid_nic[0]["ip"], 9005) is False:
            time.sleep(1)
            if time.time() - start > 10:
                break
        assert helper.check_if_port_in_use(valid_nic[0]["ip"], 9005) is True

        # Connect to wrong interface
        try:
            rsp = requests.get("http://{}:9005/admin".format(valid_nic[1]["ip"]))
        except requests.exceptions.ConnectionError:
            pass
        else:
            assert False

        # Connect to correct interface
        rsp = requests.get("http://{}:9005/admin".format(valid_nic[0]["ip"]))
        assert rsp.status_code == 200
