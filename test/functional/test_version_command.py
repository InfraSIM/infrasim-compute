#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test infrasim-main version command to check the output
matches the correct format
"""

import unittest
import re

from infrasim import run_command

version_cmd = "infrasim-main version"


class test_version_command(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_infrasim_ver(self):
        try:
            str_output = run_command(version_cmd)[1]
            if 'failed' in str_output:
                assert False
            version_list = str_output.split('\n')
            for i in range(len(version_list)-1):
                version_list[i] = version_list[i].split(':')[1]

            assert re.search('linux ([0-9]+.){2}[0-9]+', version_list[0], re.I)\
                   is not None
            assert re.search('[0-9]+.[0-9]+', version_list[1]) is not None
            assert re.search('qemu .* ([0-9]+.){2}[0-9]+', version_list[2], re.I)\
                   is not None
            assert re.search('ipmi .* ([0-9]+.){2}[0-9]+', version_list[3], re.I)\
                   is not None
            assert re.search('socat .* ([0-9]+.){3}[0-9]+', version_list[4], re.I)\
                   is not None
            assert re.search('infrasim-compute .* ([0-9]+.){2}[0-9]', version_list[5], re.I)\
                   is not None
        except Exception as e:
            print e
            assert False
