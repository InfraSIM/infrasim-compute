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
from infrasim import vm
from infrasim import ipmi
from infrasim import socat
from infrasim import run_command

def test_qemu_exist():
    code, result = run_command('which /usr/local/bin/qemu-system-x86_64', True, None, None)
    assert code == 0

def test_ipmi_exist():
    code, result = run_command('which /usr/local/bin/ipmi_sim', True, None, None)
    assert code == 0

def test_socat_exist():
    code, result = run_command('which /usr/bin/socat', True, None, None)
    assert code == 0

def test_ipmi_process_start():
    ipmi.start_ipmi("quanta_d51")
    time.sleep(5)
    code, result = run_command("pidof ipmi_sim")
    assert code == 0

def test_qemu_process_start():
    code, result = run_command("pidof qemu-system-x86_64")
    assert code == 0

def test_qemu_prcess_stop():
    vm.stop_vm("quanta_d51")
    code, result = run_command("pidof qemu-system-x86_64")
    assert code != 0

def test_ipmi_process_stop():
    ipmi.stop_ipmi()
    code, result = run_command("pidof ipmi_sim")
    assert code != 0

def test_socat_process_start():
     socat.start_socat()
     code, result = run_command("pidof socat")
     assert code == 0

def test_socat_process_stop():
     socat.stop_socat()
     code,result = run_command("pidof socat")
     assert code != 0
