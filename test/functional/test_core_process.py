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
import unittest
import os
import subprocess
import re
from infrasim import vm
from infrasim import ipmi

VIR_ERR_NO_DOMAIN = 42


def run_command(cmd="", shell=True, stdin=None, stdout=None, stderr=None):
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    print 'cmd_result:', cmd_result
    print 'child.returncode:', child.returncode
    return cmd_return_code, cmd_result


def test_qemu_exist():
    assert subprocess.call('which qemu-system-x86_64', shell=True) == 0


def test_ipmi_exist():
    assert subprocess.call('which ipmi_sim', shell=True) == 0


class test_qemu(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        v = vm.VM()
        vm.start_vm(v.render_vm_template())

    @classmethod
    def tearDownClass(cls):
        if vm.status_vm('quanta_d51'):
            vm.stop_vm('quanta_d51')

    def test_qemu_process_start(self):

        # Check via libvert
        self.assertTrue(vm.status_vm('quanta_d51'))

        # Check via system ps
        rsp = subprocess.check_output('ps aux | grep qemu', shell=True)
        self.assertIn('qemu-system-x86_64', rsp)

    def test_qemu_process_stop(self):
        vm.stop_vm('quanta_d51')

        # Check via libvert
        self.assertFalse(vm.status_vm('quanta_d51'))

        # Check via system ps
        rsp = subprocess.check_output('ps aux | grep qemu', shell=True)
        self.assertNotIn('qemu-system-x86_64', rsp)


class test_ipmi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        run_command('sudo infrasim-ipmi start')

    @classmethod
    def tearDownClass(cls):
        run_command('sudo infrasim-ipmi stop')

    def test_ipmi_process_start(self):

        # Check via lib
        self.assertEqual(ipmi.ipmi_status(), 1)

        # Check via system ps
        rsp = subprocess.check_output('ps aux | grep ipmi', shell=True)
        p = r'ipmi_sim\s+-c\s+/etc/infrasim/vbmc.conf\s.*'
        r = re.compile(p)
        self.assertIsNotNone(r.search(rsp), msg='No ipmi_sim in response data:\n{}'.format(rsp))

    def test_ipmi_process_stop(self):
        ipmi.ipmi_stop()

        # Check via lib
        self.assertEqual(ipmi.ipmi_status(), 0)

        # Check via system ps
        rsp = subprocess.check_output('ps aux | grep ipmi', shell=True)
        p = r'ipmi_sim\s.*-c\s+/etc/infrasim/vbmc.conf\s.*'
        r = re.compile(p)
        self.assertIsNone(r.search(rsp))
