#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import with_setup
import os, subprocess

def setup_func():
    os.system("sudo infrasim-ipmi start")

def teardown_func():
    os.system("sudo infrasim-ipmi stop")

@with_setup(setup_func, teardown_func)
def test_():
    cmd = "ipmitool -H localhost -U admin -P admin fru print".split(" ")
    pipe = subprocess.check_output(cmd, shell=True)
    print pipe
