#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import unittest
import yaml
import infrasim.config as config
from infrasim import run_command
from test.fixtures import FakeConfig
import infrasim.model as model
from infrasim.workspace import Workspace
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





