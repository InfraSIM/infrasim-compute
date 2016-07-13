#!/usr/bin/env python
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
import time
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import run_command
import time
from nose.tools import assert_raises

def test_qemu_exist():
    try:
        run_command('which /usr/local/bin/qemu-system-x86_64', True, None, None)
        assert True
    except:
        assert False

def test_ipmi_exist():
    try:
        run_command('which /usr/local/bin/ipmi_sim', True, None, None)
        assert True
    except:
        assert False

def test_socat_exist():
    try:
        run_command('which /usr/bin/socat', True, None, None)
        assert True
    except:
        assert False

def test_socat_process_start():
     try:
         socat.start_socat()
         ipmi.start_ipmi("quanta_d51")
         time.sleep(3)
         code, result = run_command("pidof socat")
         assert code == 0
     except:
         assert False

def test_ipmi_process_start():
    try:
        code, result = run_command("pidof ipmi_sim")
        assert code == 0
    except:
        assert False

def test_qemu_process_start():
    try:
        code, result = run_command("pidof qemu-system-x86_64")
        assert code == 0
    except:
        assert False

def test_qemu_prcess_stop():
    try:
        qemu.stop_qemu()
        run_command("pidof qemu-system-x86_64")
        assert False
    except:
        assert True

def test_ipmi_process_stop():
    try:
        ipmi.stop_ipmi()
        run_command("pidof ipmi_sim")
        assert False
    except:
        assert True

def test_socat_process_stop():
     try:
         socat.stop_socat()
         run_command("pidof socat")
         assert False
     except:
         assert True
