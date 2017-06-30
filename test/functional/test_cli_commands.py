#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import unittest
import subprocess
import yaml
import re
import time
import infrasim.config as config
from infrasim import run_command, run_command_with_user_input, CommandRunFailed
from test.fixtures import FakeConfig
import infrasim.model as model
from infrasim.workspace import Workspace
from test import fixtures


old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    os.system("pkill socat")
    os.system("pkill ipmi")
    os.system("pkill qemu")
    os.environ["PATH"] = old_path


class test_node_cli(unittest.TestCase):
    node_name = "default"
    node_workspace = os.path.join(config.infrasim_home, node_name)

    def tearDown(self):
        os.system("infrasim node destroy {}".format(self.node_name))
        os.system("rm -rf {}".format(self.node_workspace))
        os.system("pkill socat")
        os.system("pkill ipmi")
        os.system("pkill qemu")

    def test_start_status_stop_status_destroy_status(self):
        """
        CLI test: start, stop and destroy a node and check status respectively
        """
        output_status = {}

        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_status["start"] = run_command("infrasim node status")
        self.assertEqual(output_status["start"][0], 0)

        output_stop = run_command("infrasim node stop")
        self.assertEqual(output_stop[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_status["stop"] = run_command("infrasim node status")
        self.assertEqual(output_status["stop"][0], 0)

        output_destroy = run_command("infrasim node destroy")
        self.assertEqual(output_destroy[0], 0)
        self.assertFalse(Workspace.check_workspace_exists(self.node_name))

        output_status["destroy"] = run_command("infrasim node status")
        self.assertEqual(output_status["destroy"][0], 0)

        assert "{}-socat starts to run".format(self.node_name) in output_start[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_start[1]
        assert "{}-node is running".format(self.node_name) in output_start[1]

        assert "{}-socat is running".format(self.node_name) in output_status["start"][1]
        assert "{}-bmc is running".format(self.node_name) in output_status["start"][1]
        assert "{}-node is running".format(self.node_name) in output_status["start"][1]

        assert "{}-socat stop".format(self.node_name) in output_stop[1]
        assert "{}-bmc stop".format(self.node_name) in output_stop[1]
        assert "{}-node stop".format(self.node_name) in output_stop[1]

        assert "{}-socat is stopped".format(self.node_name) in output_status["stop"][1]
        assert "{}-bmc is stopped".format(self.node_name) in output_status["stop"][1]
        assert "{}-node is stopped".format(self.node_name) in output_status["stop"][1]

        assert "Node {} runtime workspace is destroyed".format(self.node_name) in output_destroy[1]

        assert "Node {} runtime workspace doesn't exist".format(self.node_name) in output_status["destroy"][1]

    def test_start_status_restart_status_destroy_status(self):
        """
        CLI test: start, restart and destroy a node and check status respectively
        """
        output_status = {}

        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_status["start"] = run_command("infrasim node status")
        self.assertEqual(output_status["start"][0], 0)

        output_restart = run_command("infrasim node restart")
        self.assertEqual(output_restart[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_status["restart"] = run_command("infrasim node status")
        self.assertEqual(output_status["restart"][0], 0)

        output_destroy = run_command("infrasim node destroy")
        self.assertEqual(output_destroy[0], 0)
        self.assertFalse(Workspace.check_workspace_exists(self.node_name))

        output_status["destroy"] = run_command("infrasim node status")
        self.assertEqual(output_status["destroy"][0], 0)

        assert "{}-socat starts to run".format(self.node_name) in output_start[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_start[1]
        assert "{}-node is running".format(self.node_name) in output_start[1]

        assert "{}-socat is running".format(self.node_name) in output_status["start"][1]
        assert "{}-bmc is running".format(self.node_name) in output_status["start"][1]
        assert "{}-node is running".format(self.node_name) in output_status["start"][1]

        assert "{}-socat stop".format(self.node_name) in output_restart[1]
        assert "{}-bmc stop".format(self.node_name) in output_restart[1]
        assert "{}-node stop".format(self.node_name) in output_restart[1]

        assert "{}-socat starts to run".format(self.node_name) in output_restart[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_restart[1]
        assert "{}-node is running".format(self.node_name) in output_restart[1]

        assert "{}-socat is running".format(self.node_name) in output_status["restart"][1]
        assert "{}-bmc is running".format(self.node_name) in output_status["restart"][1]
        assert "{}-node is running".format(self.node_name) in output_status["restart"][1]

        assert "Node {} runtime workspace is destroyed".format(self.node_name) in output_destroy[1]

        assert "Node {} runtime workspace doesn't exist".format(self.node_name) in output_status["destroy"][1]

    def test_start_destroy(self):
        """
        CLI test: start, then destroy the node directly
        """
        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_destroy = run_command("infrasim node destroy")
        self.assertEqual(output_destroy[0], 0)
        self.assertFalse(Workspace.check_workspace_exists(self.node_name))

        assert "{}-socat starts to run".format(self.node_name) in output_start[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_start[1]
        assert "{}-node is running".format(self.node_name) in output_start[1]

        assert "Node {} runtime workspace is destroyed".format(self.node_name) in output_destroy[1]

    def test_destory_destroy(self):
        """
        CLI test: fail to destroy a destroyed node
        """
        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_destroy_1 = run_command("infrasim node destroy")
        self.assertEqual(output_destroy_1[0], 0)
        self.assertFalse(Workspace.check_workspace_exists(self.node_name))

        output_destroy_2 = run_command("infrasim node destroy")
        self.assertEqual(output_destroy_2[0], 0)
        self.assertFalse(Workspace.check_workspace_exists(self.node_name))

        assert "Node {} runtime workspace is destroyed".format(self.node_name) in output_destroy_1[1]
        assert "Node {} runtime workspace is not found".format(self.node_name) in output_destroy_2[1]

    def test_start_start(self):
        """
        CLI test: start a started node will hint it's running
        """
        output_start_1 = run_command("infrasim node start")
        self.assertEqual(output_start_1[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_start_2 = run_command("infrasim node start")
        self.assertEqual(output_start_2[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        assert "{}-socat starts to run".format(self.node_name) in output_start_1[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_start_1[1]
        assert "{}-node is running".format(self.node_name) in output_start_1[1]

        assert "{}-socat is already running".format(self.node_name) in output_start_2[1]
        assert "{}-bmc is already running".format(self.node_name) in output_start_2[1]
        assert "{}-node is running".format(self.node_name) in output_start_2[1]

    def test_stop_stop(self):
        """
        CLI test: stop a node will hint it's already stopped
        """
        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_stop_1 = run_command("infrasim node stop")
        self.assertEqual(output_stop_1[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        output_stop_2 = run_command("infrasim node stop")
        self.assertEqual(output_stop_2[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))

        assert "{}-socat starts to run".format(self.node_name) in output_start[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_start[1]
        assert "{}-node is running".format(self.node_name) in output_start[1]

        assert "{}-socat stop".format(self.node_name) in output_stop_1[1]
        assert "{}-bmc stop".format(self.node_name) in output_stop_1[1]
        assert "{}-node stop".format(self.node_name) in output_stop_1[1]

        assert "[        ] {}-node is stopped".format(self.node_name) in output_stop_2[1]
        assert "[        ] {}-bmc is stopped".format(self.node_name) in output_stop_2[1]
        assert "[        ] {}-socat is stopped".format(self.node_name) in output_stop_2[1]

    def test_start_info_destroy_info(self):
        """
        CLI test: start and destroy a node, and get node_info respectively
        """
        output_info = {}
        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))
        output_info['start'] = run_command("infrasim node info")
        self.assertEqual(output_info['start'][0], 0)

        output_destroy = run_command("infrasim node destroy")
        self.assertEqual(output_destroy[0], 0)
        self.assertFalse(Workspace.check_workspace_exists(self.node_name))

        output_info['destroy'] = run_command("infrasim node info")
        self.assertEqual(output_info['destroy'][0], 0)

        assert "{}-socat starts to run".format(self.node_name) in output_start[1]
        assert "{}-bmc starts to run".format(self.node_name) in output_start[1]
        assert "{}-node is running".format(self.node_name) in output_start[1]

        assert "node name:          {}".format(self.node_name) in output_info['start'][1]
        assert "type:" in output_info['start'][1]
        assert "memory size:" in output_info['start'][1]
        assert "sol_enable:" in output_info['start'][1]
        assert "cpu quantities:" in output_info['start'][1]
        assert "cpu type:" in output_info['start'][1]
        assert "network(s):" in output_info['start'][1]
        assert "device" in output_info['start'][1]
        assert "mode" in output_info['start'][1]
        assert "name " in output_info['start'][1]
        assert "storage backend:" in output_info['start'][1]
        assert "type " in output_info['start'][1]
        assert "max drive" in output_info['start'][1]
        assert "drive size" in output_info['start'][1]

        assert "Node {} runtime workspace is destroyed".format(self.node_name) in output_destroy[1]

        assert "Node {} runtime workspace doesn't exist".format(self.node_name) in output_info['destroy'][1]

    def test_init(self):
        """
        CLI test: test init "-f" which will remove existing workspace
        """
        output_info = {}
        output_start = run_command("infrasim node start")
        self.assertEqual(output_start[0], 0)
        self.assertTrue(Workspace.check_workspace_exists(self.node_name))
        output_info['start'] = run_command("infrasim node info")
        self.assertEqual(output_info['start'][0], 0)

        self.assertRaises(CommandRunFailed, run_command,
                          cmd="infrasim init -s", shell=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        run_command("infrasim init -s -f")
        self.assertEqual(len(os.listdir(config.infrasim_home)), 1)

        # Verify if it will reinstall packages when user confirmed 'Y'
        result = run_command_with_user_input("infrasim init", True, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE, "Y\nY\nY\n")
        assert "downloading Qemu" in result[1]
        assert "downloading OpenIpmi" in result[1]
        assert "downloading Seabios" in result[1]

        result = run_command_with_user_input("infrasim init", True, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE, "Y\nyes\nn\n")
        assert "downloading Qemu" in result[1]
        assert "downloading OpenIpmi" in result[1]
        assert "downloading Seabios" not in result[1]

        result = run_command_with_user_input("infrasim init", True, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE, "no\nN\nY\n")
        assert "downloading Qemu" not in result[1]
        assert "downloading OpenIpmi" not in result[1]
        assert "downloading Seabios" in result[1]


class test_config_cli_with_runtime_node(unittest.TestCase):
    test_name = "test"
    test_workspace = os.path.join(config.infrasim_home, test_name)
    test_runtime_yml = os.path.join(test_workspace, "etc", "infrasim.yml")
    test_config_path = "test.yml"

    def setUp(self):
        node_info = FakeConfig().get_node_info()
        with open(self.test_config_path, "w") as fp:
            yaml.dump(node_info, fp, default_flow_style=False)
        os.system("infrasim config add {} {}".format(self.test_name, self.test_config_path))
        os.system("infrasim node start {}".format(self.test_name))
        os.system("infrasim node stop {}".format(self.test_name))

    def tearDown(self):
        os.system("infrasim node destroy {}".format(self.test_name))
        os.system("rm -rf {}".format(self.test_workspace))
        os.system("pkill socat")
        os.system("pkill ipmi")
        os.system("pkill qemu")

    def test_update_config_then_start_node(self):
        """
        CLI test: node won't apply updated config if there's runtime workspace
        """
        node_info = FakeConfig().get_node_info()
        node_info["type"] = "dell_r730xd"
        with open(self.test_config_path, "w") as fp:
            yaml.dump(node_info, fp, default_flow_style=False)

        output_update = run_command("infrasim config update {} {}".format(self.test_name, self.test_config_path))
        self.assertEqual(output_update[0], 0)
        output_start = run_command("infrasim node start {}".format(self.test_name))
        self.assertEqual(output_start[0], 0)
        output_ps_qemu = run_command("ps ax | grep qemu")
        self.assertEqual(output_ps_qemu[0], 0)

        assert "Node {}'s configuration mapping is updated".format(self.test_name) in output_update[1]
        assert "dell_r730xd" not in output_ps_qemu[1]

    def test_delete_config_then_start_node(self):
        """
        CLI test: node will start even config is deleted if there is runtime workspace
        """
        output_delete = run_command("infrasim config delete {}".format(self.test_name))
        self.assertEqual(output_delete[0], 0)
        output_start = run_command("infrasim node start {}".format(self.test_name))
        self.assertEqual(output_start[0], 0)

        assert "Node {}'s configuration mapping removed".format(self.test_name) in output_delete[1]
        assert "{}-socat starts to run".format(self.test_name) in output_start[1]
        assert "{}-bmc starts to run".format(self.test_name) in output_start[1]
        assert "{}-node is running".format(self.test_name) in output_start[1]


class test_config_cli_without_runtime_node(unittest.TestCase):
    test_name = "test"
    test_workspace = os.path.join(config.infrasim_home, test_name)
    test_runtime_yml = os.path.join(test_workspace, "etc", "infrasim.yml")
    test_config_path = "test.yml"

    def setUp(self):
        node_info = FakeConfig().get_node_info()
        with open(self.test_config_path, "w") as fp:
            yaml.dump(node_info, fp, default_flow_style=False)
        os.system("infrasim config add {} {}".format(self.test_name, self.test_config_path))

    def tearDown(self):
        os.system("infrasim node destroy {}".format(self.test_name))
        os.system("rm -rf {}".format(self.test_workspace))
        os.system("pkill socat")
        os.system("pkill ipmi")
        os.system("pkill qemu")

    def test_update_config_then_start_node(self):
        """
        CLI test: node will apply updated config if there's no runtime workspace
        """
        node_info = FakeConfig().get_node_info()
        node_info["type"] = "dell_r730xd"
        with open(self.test_config_path, "w") as fp:
            yaml.dump(node_info, fp, default_flow_style=False)

        output_update = run_command("infrasim config update {} {}".format(self.test_name, self.test_config_path))
        self.assertEqual(output_update[0], 0)
        output_start = run_command("infrasim node start {}".format(self.test_name))
        self.assertEqual(output_start[0], 0)
        output_ps_qemu = run_command("ps ax | grep qemu")
        self.assertEqual(output_ps_qemu[0], 0)

        assert "Node {}'s configuration mapping is updated".format(self.test_name) in output_update[1]
        assert "dell_r730xd" in output_ps_qemu[1]

    def test_delete_config_then_start_node(self):
        """
        CLI test: node will not start after config is deleted if there is no runtime workspace
        """
        output_delete = run_command("infrasim config delete {}".format(self.test_name))
        self.assertEqual(output_delete[0], 0)
        output_start = run_command("infrasim node start {}".format(self.test_name))
        self.assertEqual(output_start[0], 0)

        assert "Node {}'s configuration mapping removed".format(self.test_name) in output_delete[1]
        assert "Node {}'s configuration is not defined.".format(self.test_name) in output_start[1]


class test_command_navigation(unittest.TestCase):

    def test_infrasim(self):
        """
        CLI test: "infrasim -h" navigates next level command usage
        """
        p = r'\{([a-zA-Z,]+)\}'
        cmd_next_level = ["node", "chassis", "config", "init", "version", "global"]

        output = run_command("infrasim -h")[1]
        r = re.compile(p)
        m = r.search(output)
        cmd = m.group(1)
        cmd_list = cmd.split(',')
        assert set(cmd_list) == set(cmd_next_level)

    def test_infrasim_node(self):
        """
        CLI test: "infrasim node -h" navigates next level command usage
        """
        p = r'\{([a-zA-Z,]+)\}'
        cmd_next_level = ["destroy", "info", "status", "start", "stop", "restart"]

        output = run_command("infrasim node -h")[1]
        r = re.compile(p)
        m = r.search(output)
        cmd = m.group(1)
        cmd_list = cmd.split(',')
        assert set(cmd_list) == set(cmd_next_level)

    def test_infrasim_config(self):
        """
        CLI test: "infrasim config -h" navigates next level command usage
        """
        p = r'\{([a-zA-Z,]+)\}'
        cmd_next_level = ["add", "delete", "edit", "list", "update"]

        output = run_command("infrasim config -h")[1]
        r = re.compile(p)
        m = r.search(output)
        cmd = m.group(1)
        cmd_list = cmd.split(',')
        assert set(cmd_list) == set(cmd_next_level)


class test_global_status(unittest.TestCase):
    """
    CLI test: start, stop and destroy node test1 and test2, get the global status respectively.
    start, stop test1 ipmi-console, get the global status respectively.
    """

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.node_info = fake_config.get_node_info()
        # start node test1
        self.node_info['name'] = "test1"
        self.node_info["type"] = "quanta_d51"
        node1 = model.CNode(self.node_info)
        node1.init()
        node1.precheck()
        node1.start()
        time.sleep(2)

    def tearDown(self):
        node1 = model.CNode(self.node_info)
        node1.init()
        node1.stop()
        node1.terminate_workspace()
        self.node_info = None
        fake_config_2 = fixtures.FakeConfig()
        node_info_2 = fake_config_2.get_node_info()
        node_info_2['name'] = "test2"
        node2 = model.CNode(node_info_2)
        node2.init()
        node2.stop()
        node2.terminate_workspace()

    def test_node_global_status_ipmi_console(self):
        os.system("ipmi-console start test1")
        time.sleep(2)
        output_status = {}
        output_status["ipmi-console-start"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'socat', 'ipmi-console', 'ports', 'test1']
        for word in words:
            assert word in output_status["ipmi-console-start"]
        words = ['racadm', 'test2']
        for word in words:
            assert word not in output_status["ipmi-console-start"]

        os.system("ipmi-console stop test1")
        output_status["ipmi-console-stop"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'socat', 'ports', 'test1']
        for word in words:
            assert word in output_status["ipmi-console-stop"]
        words = ['racadm', 'ipmi-console', 'test2']
        for word in words:
            assert word not in output_status["ipmi-console-stop"]

    def test_nodes_global_status_start_stop_destroy(self):

        output_status = {}
        output_status["start1"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'socat', 'ports', 'test1']
        for word in words:
            assert word in output_status["start1"]
        words = ['racadm', 'ipmi-console', 'test2']
        for word in words:
            assert word not in output_status["start1"]

        fake_config_2 = fixtures.FakeConfig()
        node_info_2 = fake_config_2.get_node_info()
        node_info_2['name'] = "test2"
        node_info_2['ipmi_console_ssh'] = 9301
        node_info_2['ipmi_console_port'] = 9001
        node_info_2['bmc_connection_port'] = 9101
        node_info_2['compute']['vnc_display'] = 2
        node_info_2['compute']['monitor'] = {
            'mode': 'readline',
            'chardev': {
                'backend': 'socket',
                'host': '127.0.0.1',
                'port': 2346,
                'server': True,
                'wait': False
            }
        }
        node_info_2["type"] = "dell_c6320"
        node2 = model.CNode(node_info_2)
        node2.init()
        node2.precheck()
        node2.start()
        time.sleep(2)
        output_status["start"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'socat', 'racadm', 'ports', 'test1', 'test2']
        for word in words:
            assert word in output_status["start"]
        assert 'ipmi-console' not in output_status['start']

        node1 = model.CNode(self.node_info)
        node1.init()
        node1.stop()
        output_status["stop1"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'socat', 'racadm', 'ports', 'test1', 'test2']
        for word in words:
            assert word in output_status["stop1"]
        assert 'ipmi-console' not in output_status['stop1']

        node2.stop()
        output_status["stop"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'ports', 'test1', 'test2']
        for word in words:
            assert word in output_status["stop"]
        words = ['socat', 'racadm', 'ipmi-console']
        for word in words:
            assert word not in output_status['stop']

        node1.terminate_workspace()
        output_status["destroy1"] = run_command("infrasim global status")[1]
        words = ['name', 'bmc', 'node', 'ports', 'test2']
        for word in words:
            assert word in output_status["destroy1"]
        words = ['socat', 'racadm', 'ipmi-console', 'test1']
        for word in words:
            assert word not in output_status['destroy1']

        node2.terminate_workspace()
        output_status["destroy"] = run_command("infrasim global status")[1]
        assert ("test1" not in output_status["destroy"]) and (
            "test2" not in output_status["destroy"])
