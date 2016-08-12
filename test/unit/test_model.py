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
            cpu.handle_parms()
            assert "-cpu Haswell" in cpu.get_option()
            assert "-smp 2" in cpu.get_option()
        except:
            assert False

    def test_set_vcpu_no_value(self):
        pass
