#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

"""
Test infrasim-main start command to check the output
matches the correct format
"""

import subprocess
import unittest
import re

from infrasim import run_command
from infrasim import helper


class test_start_intf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_ip4addr_list(self):
        ip_list = []

        try:
            test_ip_list = helper.ip4_addresses()

            assert test_ip_list

            str_result = run_command('hostname -I', True, \
                                 subprocess.PIPE, subprocess.PIPE)[1]

            host_ip = str_result.split()

            # Verify IP address, except 127.0.0.1, both lists share
            # same set of ip address

            hit = True
            for ip in host_ip:
                hit = False
                for test_ip in test_ip_list:
                    if ip == test_ip:
                        hit = True
                        break

                assert hit

        except Exception as e:
            print e
            assert False
