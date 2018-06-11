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
import json
from infrasim import model
from test import fixtures
from infrasim import helper
import requests
import time

TMP_CONF_FILE = "/tmp/test.yml"
form_drive_name = "scsi0-0-{}-0"


def run_command(cmd="", shell=True, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell,
                             stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_infrasim_monitor(unittest.TestCase):

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

    def test_hmp_access(self):
        # start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        node_name = node.get_node_name()
        port = self.conf["monitor"].get("port", 9005)

        if self.conf["monitor"].get("interface", None):
            interface = self.conf["monitor"].get("interface", None)
            ip = helper.get_interface_ip(interface)
        else:
            ip = "0.0.0.0"

        assert self.wait_port_up(ip, 9005)
        interface = self.conf["monitor"].get("interface",)
        payload = {
            "execute": "human-monitor-command",
            "arguments": {
                "command-line": "info chardev"
            }
        }
        url = "http://{}:{}/hmp/{}".format(ip, port, node_name)
        headers = {'content-type': 'application/json'}
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=1)
        # res = requests.post(url)
        if res.status_code == requests.codes.ok:
            return True
        else:
            return False

    def test_qmp_access(self):
        # start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        node_name = node.get_node_name()
        port = self.conf["monitor"].get("port", 9005)

        if self.conf["monitor"].get("interface", None):
            interface = self.conf["monitor"].get("interface", None)
            ip = helper.get_interface_ip(interface)
        else:
            ip = "0.0.0.0"

        assert self.wait_port_up(ip, 9005)
        interface = self.conf["monitor"].get("interface",)
        payload = {
            "execute": "query-status"
        }
        url = "http://{}:{}/qmp/{}".format(ip, port, node_name)
        headers = {'content-type': 'application/json'}
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=1)
        if res.status_code == requests.codes.ok:
            return True
        else:
            return False

    def test_robust_error_hmp(self):
        # start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        node_name = node.get_node_name()
        port = self.conf["monitor"].get("port", 9005)

        if self.conf["monitor"].get("interface", None):
            interface = self.conf["monitor"].get("interface", None)
            ip = helper.get_interface_ip(interface)
        else:
            ip = "0.0.0.0"

        assert self.wait_port_up(ip, 9005)
        interface = self.conf["monitor"].get("interface",)
        # send the error command
        payload = {
            "error": "error"
        }
        url = "http://{}:{}/hmp/{}".format(ip, port, node_name)
        headers = {'content-type': 'application/json'}

        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=1)
        if res.status_code == requests.codes.ok:
            return True
        else:
            return False

    def test_robust_error_qmp(self):
        # start service
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        node_name = node.get_node_name()
        port = self.conf["monitor"].get("port", 9005)

        if self.conf["monitor"].get("interface", None):
            interface = self.conf["monitor"].get("interface", None)
            ip = helper.get_interface_ip(interface)
        else:
            ip = "0.0.0.0"

        assert self.wait_port_up(ip, 9005)
        interface = self.conf["monitor"].get("interface",)
        # send the error command
        payload = {
            "error": "error"
        }
        url = "http://{}:{}/qmp/{}".format(ip, port, node_name)
        headers = {'content-type': 'application/json'}

        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=1)
        if res.status_code == requests.codes.ok:
            return True
        else:
            return False
