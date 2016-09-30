#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

"""
Test infrasim-main version command to check the output
matches the correct format
"""

import unittest
import re

from infrasim import run_command
from infrasim import main


class test_version_command(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_infrasim_ver(self):
        try:
            str_output = main.version()
            if 'failed' in str_output:
                assert False
            version_list = str_output.split('\n')
            for i in range(len(version_list)-1):
                version_list[i] = version_list[i].split(':')[1].strip()
            self.assertIsNotNone(
                re.search('Linux (\d+\.){2}\d+', version_list[0]),
                "kernel version is '{}', not expected".format(version_list[0])
            )
            self.assertIsNotNone(
                re.search('\d+.\d+', version_list[1]),
                "base OS version is '{}', not expected".format(version_list[1])
            )
            self.assertIsNotNone(
                re.search(
                    'QEMU emulator version infrasim-qemu_(\d+.){2}\d+',
                    version_list[2]
                ),
                "qemu version is '{}', not expected".format(version_list[2])
            )
            self.assertIsNotNone(
                re.search(
                    'IPMI Simulator version infrasim-openipmi_(\d+.){2}\d+',
                    version_list[3]
                ),
                "openipmi version is '{}', not expected".format(
                    version_list[3]))
            self.assertIsNotNone(
                re.search('socat version (\d+.){3}\d+', version_list[4]),
                "socat version is '{}', not expected".format(version_list[4])
            )
            self.assertIsNotNone(
                re.search(
                    'infrasim-compute version (\d+.){2}\d',
                    version_list[5]
                ),
                "infrasim-compute version is '{}', not expected".format(
                    version_list[5])
            )

        except AssertionError, e:
            print e
            assert False
        except Exception as e:
            print e
            assert False
