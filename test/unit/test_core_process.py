#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
"""
Test InfraSIM core component:
    - QEMU
    - ipmi
    - ...
Check:
    - binary exist
    - corresponding process can be started by start service
    - corresponding process can be ended by stop service
"""

from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import model
from infrasim import config
import time
import yaml
import os


def setUp():
    workspace = "{}/.infrasim/node-0".format(os.environ["HOME"])
    if os.path.exists(workspace):
        os.system("rm -rf {}".format(workspace))
    with open(config.infrasim_initial_config, 'r') as f_yml:
        conf = yaml.load(f_yml)
    node = model.CNode(conf)
    node.init_workspace()


def tearDown():
    workspace = "{}/.infrasim/node-0".format(os.environ["HOME"])
    if os.path.exists(workspace):
        os.system("rm -rf {}".format(workspace))


def test_qemu_exist():
    try:
        qemu.get_qemu()
        assert True
    except:
        assert False


def test_ipmi_exist():
    try:
        ipmi.get_ipmi()
        assert True
    except:
        assert False


def test_socat_exist():
    try:
        socat.get_socat()
        assert True
    except:
        assert False


def test_socat_process_start():
    try:
        socat.start_socat()
        time.sleep(2)
        socat.status_socat()
        assert True
    except:
        assert False


def test_ipmi_process_start():
    try:
        ipmi.start_ipmi()
        time.sleep(2)
        ipmi.status_ipmi()
        assert True
    except:
        assert False


def test_qemu_process_start():
    try:
        qemu.status_qemu()
        assert True
    except:
        assert False


def test_qemu_process_status_running():
    try:
        qemu.status_qemu()
        assert True
    except:
        assert False


def test_ipmi_process_status_running():
    try:
        ipmi.status_ipmi()
        assert True
    except:
        assert False


def test_socat_process_status_running():
    try:
        socat.status_socat()
        assert True
    except:
        assert False


def test_qemu_prcess_stop():
    try:
        qemu.stop_qemu()
        qemu.status_qemu()
        assert False
    except:
        assert True


def test_ipmi_process_stop():
    try:
        ipmi.stop_ipmi()
        ipmi.status_ipmi()
        assert False
    except:
        assert True


def test_socat_process_stop():
     try:
         socat.stop_socat()
         socat.status_socat()
         assert False
     except:
         assert True
