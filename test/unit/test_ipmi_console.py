#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

from infrasim.ipmicons import sdr
from infrasim.ipmicons.command import Command_Handler
from infrasim.ipmicons import common
from infrasim.model import CNode
from infrasim import config
from test import fixtures
import unittest
import yaml
import shutil
import time
import os

ch = Command_Handler()


class test_ipmi_console(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_sensor_value_get_discrete(self):
        sensor_d = sdr.build_sensors(name="discrete_sample",
                                     ID=0x10,
                                     mc=32,
                                     value="0xca10",
                                     tp=0x00)
        sensor_d.set_event_type(0x6f)

        ch.get_sensor_value(["0x10"])
        assert "0xca10" in common.msg_queue.get()

    def test_sensor_value_get_analog(self):
        sensor_a = sdr.build_sensors(name="analog_sample",
                                     ID=0x11,
                                     mc=32,
                                     value=0x63,
                                     tp=0x00)
        sensor_a.set_event_type(0x01)
        sensor_a.set_m_lb(0x58)
        sensor_a.set_m_ub(0x00)
        sensor_a.set_b_lb(0x00)
        sensor_a.set_b_ub(0x00)
        sensor_a.set_exp(0x00)
        sensor_a.set_su2(18)

        ch.get_sensor_value(["0x11"])
        assert "analog_sample : 8712.000 RPM" in common.msg_queue.get()


class test_ipmi_console_default_env(unittest.TestCase):

    TMP_CONF_FILE = "/tmp/test.yml"
    bmc_conf = ""

    @classmethod
    def setUpClass(cls):
        node_info = {}
        fake_config = fixtures.FakeConfig()
        node_info = fake_config.get_node_info()
        cls.bmc_conf = os.path.join(os.environ["HOME"], ".infrasim",
                                    node_info["name"], "data", "vbmc.conf")

        with open(cls.TMP_CONF_FILE, "w") as f:
            yaml.dump(node_info, f, default_flow_style=False)

        node = CNode(node_info)
        node.init()
        node.precheck()
        node.start()

        # Wait ipmi_sim start.
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):

        with open(cls.TMP_CONF_FILE, "r") as yml_file:
            node_info = yaml.load(yml_file)

        node = CNode(node_info)
        node.init()
        node.stop()

        if os.path.exists(cls.TMP_CONF_FILE):
            os.unlink(cls.TMP_CONF_FILE)

        workspace = os.path.join(config.infrasim_home, "test")
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    def test_ipmi_console_env(self):
        common.init_env("test")
        assert common.env.PORT_SSH_FOR_CLIENT == 9300
        assert common.env.PORT_TELNET_TO_VBMC == 9000
        assert common.env.VBMC_IP == "localhost"
        assert common.env.VBMC_PORT == 623


class test_ipmi_console_customized_env(unittest.TestCase):

    TMP_CONF_FILE = "/tmp/test.yml"
    bmc_conf = ""

    @classmethod
    def setUpClass(cls):
        node_info = {}
        fake_config = fixtures.FakeConfig()
        node_info = fake_config.get_node_info()
        node_info["bmc"] = {}
        node_info["bmc"]["interface"] = "lo"
        node_info["bmc"]["ipmi_over_lan_port"] = 625
        node_info["ipmi_console_ssh"] = 9401
        node_info["ipmi_console_port"] = 9101
        cls.bmc_conf = os.path.join(os.environ["HOME"], ".infrasim",
                                    node_info["name"], "data", "vbmc.conf")

        with open(cls.TMP_CONF_FILE, "w") as f:
            yaml.dump(node_info, f, default_flow_style=False)

        node = CNode(node_info)
        node.init()
        node.precheck()
        node.start()

        # Wait ipmi_sim start.
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):

        with open(cls.TMP_CONF_FILE, "r") as yml_file:
            node_info = yaml.load(yml_file)

        node = CNode(node_info)
        node.init()
        node.stop()

        if os.path.exists(cls.TMP_CONF_FILE):
            os.unlink(cls.TMP_CONF_FILE)

        workspace = os.path.join(config.infrasim_home, "test")
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    def test_ipmi_console_env(self):
        common.init_env("test")
        assert common.env.PORT_SSH_FOR_CLIENT == 9401
        assert common.env.PORT_TELNET_TO_VBMC == 9101
        assert common.env.VBMC_IP == "127.0.0.1"
        assert common.env.VBMC_PORT == 625
