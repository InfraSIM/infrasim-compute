#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

"""
Test serial functions:
    - socat can create serial device
    - qemu connect to it
    - SOL (serial over lan) work as expected
"""
import unittest
import os
import yaml
from infrasim import socat
from infrasim import config


class test_serial(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        socat.stop_socat()

    def setUp(self):
        os.system("touch test.yml")
        with open(config.infrasim_initial_config, 'r') as f_yml:
            self.conf = yaml.load(f_yml)

    def tearDown(self):
        self.conf = None
        socat.stop_socat()
        os.system("rm -rf {}/.infrasim/node-0/".format(os.environ["HOME"]))
        os.system("rm -rf test.yml")

    def test_socat_create_serial_device_file(self):
        target_device = "./pty_serial"
        if os.path.isfile(target_device) or os.path.islink(target_device):
            os.system("rm {}".format(target_device))

        # Start socat and device shall be created
        self.conf["sol_device"] = target_device
        with open("test.yml", "w") as yaml_file:
            yaml.dump(self.conf, yaml_file, default_flow_style=False)
        socat.start_socat("test.yml")

        if os.path.islink(target_device):
            assert True
        else:
            assert False

        # Remove socat and device shall be collected
        socat.stop_socat()
        if os.path.isfile(target_device) or os.path.islink(target_device):
            assert False
        else:
            assert True
