#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest
from infrasim import ArgsNotCorrect
from infrasim import model


class qemu_functions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.system("touch test.yml")

    @classmethod
    def tearDownClass(cls):
        os.system("rm -rf test.yml")

    def test_set_cpu(self):
        try:
            cpu_info = {
                "quantities": 2,
                "type": "Haswell"
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-cpu Haswell" in cpu.get_option()
            assert "-smp 2" in cpu.get_option()
        except:
            assert False

    def test_set_cpu_no_info(self):
        try:
            cpu_info = {}

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-cpu host" in cpu.get_option()
            assert "-smp 2" in cpu.get_option()
        except:
            assert False

    def test_set_cpu_only_quantity(self):
        try:
            cpu_info = {
                "quantities": 8
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-smp 8,sockets=2,cores=4,threads=1" in cpu.get_option()
        except:
            assert False

    def test_set_cpu_negative_quantity(self):
        try:
            cpu_info = {
                "quantities": -2
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
        except ArgsNotCorrect:
            assert True
        else:
            assert False

    def test_set_cpu_feature_nx(self):
        try:
            cpu_info = {
                "features": "+nx"
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-cpu host,+nx" in cpu.get_option()
        except:
            assert False
