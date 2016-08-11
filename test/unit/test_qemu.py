#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from infrasim import qemu, ArgsNotCorrect
import unittest
import netifaces

class qemu_functions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.system("touch test.yml")

    @classmethod
    def tearDownClass(cls):
        os.system("rm -rf test.yml")

    def test_set_node(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "main:" > test.yml')
            os.system('echo "    node: quanta_d51" >> test.yml')
            vm.set_node("test.yml")
        except:
            assert False

    def test_set_node_no_value(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "" > test.yml')
            vm.set_node("test.yml")
        except ArgsNotCorrect as e:
            assert "node is not found" in e.value

    def test_set_cpu(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    cpu: Haswell" >> test.yml')
            vm.set_cpu("test.yml")
            assert True
        except:
            assert False

    def test_set_cpu_no_value(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "" > test.yml')
            vm.set_cpu("test.yml")
        except ArgsNotCorrect as e:
            assert "cpu is not found" in e.value

    def test_set_memory(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    memory: 1024" >> test.yml')
            vm.set_memory("test.yml")
            assert True
        except:
            assert False

    def test_set_memory_no_value(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "" > test.yml')
            vm.set_memory("test.yml")
        except ArgsNotCorrect as e:
            assert "memory is not found" in e.value

    def test_set_vcpu(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    vcpu: 2" >> test.yml')
            vm.set_vcpu("test.yml")
            assert True
        except:
            assert False

    def test_set_vcpu_no_value(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "" > test.yml')
            vm.set_vcpu("test.yml")
        except ArgsNotCorrect as e:
            assert "vcpu is not found" in e.value

    def test_set_networks_no_network_mode(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "" > test.yml ')
            vm.set_network("test.yml")
        except ArgsNotCorrect as e:
            assert "network_mode is not found" in e.value


    def test_set_disks_no_disk_num(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "" > test.yml ')
            vm.set_disks("test.yml")
        except ArgsNotCorrect as e:
            assert "disk_num is not found" in e.value

    def test_set_disks_no_disk_size(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    disk_num: 1" >> test.yml')
            vm.set_disks("test.yml")
        except ArgsNotCorrect as e:
            assert "disk_size is not found" in e.value

    def test_set_disks_disk_size_8G(self):
        try:
            vm = qemu.QEMU()
            os.system("rm -rf {}/*".format(os.environ['HOME'] + '/.infrasim/'))
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    disk_num: 1" >> test.yml')
            os.system('echo "    disk_size: 8" >> test.yml')
            vm.set_disks("test.yml")
            assert True
        except:
            assert False

    def test_set_networks_network_mode_wrong_name(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "    network_mode: test" >> test.yml')
            vm.set_network("test.yml")
        except ArgsNotCorrect as e:
            assert "Not supported network mode" in e.value

    def test_set_networks_network_mode_macvtap_network_name(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    network_mode: macvtap" >> test.yml')
            vm.set_network("test.yml")
        except ArgsNotCorrect as e:
            assert "network_name is not found" in e.value

    def test_set_networks_network_mode_macvtap_macs(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    network_name: lo" >> test.yml')
            os.system('echo "    network_mode: macvtap" >> test.yml')
            vm.set_network("test.yml")
        except ArgsNotCorrect as e:
            assert "No network mac address found" in e.value

    def test_create_delete_macvtap(self):
        try:
            nics_list = netifaces.interfaces()
            eth_nic = filter(lambda x: 'e' in x,nics_list)[0]
            qemu.create_macvtap(0, eth_nic, "00:1e:67:e1:e7:a4")
            qemu.stop_macvtap("macvtap0")
            assert True
        except:
            assert False

    def test_set_networks_network_mode_brdige_network_name(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    network_mode: bridge" >> test.yml')
            vm.set_network("test.yml")
        except ArgsNotCorrect as e:
            assert "network_name is not found" in e.value

    def test_set_networks_network_mode_bridge_not_exist(self):
        try:
            vm = qemu.QEMU()
            os.system('echo "---" > test.yml')
            os.system('echo "node:" > test.yml')
            os.system('echo "    network_mode: bridge" >> test.yml')
            os.system('echo "    network_name: test" >> test.yml')
            os.system('echo "    network_mac1: 00:1e:67:5b:d6:02" >> test.yml')
            vm.set_network("test.yml")
        except ArgsNotCorrect as e:
            assert "not exists" in e.value

    def test_read_from_config_with_exception(self):
        try:
            vm = qemu.QEMU()
            vm.read_from_config("test.yml")
        except ArgsNotCorrect as e:
            assert True

    def test_set_cdrom_hardware(self):
        vm = qemu.QEMU()
        vm.set_cdrom("test.yml")
        cmd = vm.get_qemu_cmd()
        if os.path.exists("/dev/sr0") is True:
            assert "-cdrom" in cmd
        else:
            assert "-cdrom" not in cmd

    def test_set_cdrom_iso(self):
        vm = qemu.QEMU()
        os.system('echo "---" > test.yml')
        os.system('echo "node:" > test.yml')
        os.system('echo "    cdrom: /tmp/test.iso" >> test.yml')
        vm.set_cdrom("test.yml")
        cmd = vm.get_qemu_cmd()
        assert "test.iso" in cmd

    def test_set_kvm_enable(self):
        vm = qemu.QEMU()
        vm.set_kvm_enable()
        cmd = vm.get_qemu_cmd()
        if os.path.exists("/dev/kvm") is True:
            assert "--enable-kvm" in cmd
        else:
            assert "--enable-kvm" not in cmd

    def test_get_qemu_cmd(self):
        vm = qemu.QEMU()
        vm.get_qemu_cmd()
        assert True
