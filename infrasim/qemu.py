#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, uuid, subprocess, ConfigParser, sys
from . import run_command

def get_qemu():
    code, qemu_cmd = run_command("which /usr/loca/bin/qemu-system-x86_64")
    if code != 0:
        raise Exception("Qemu install Error")
    return qemu_cmd.strip(os.linesep)

class QEMU():
    VM_DEFAULT_CONFIG = "/etc/infrasim/infrasim.conf"
    def __init__(self):
        self.vm_features = {"name": "quanta_d51", "memory": 1024,
                     "vcpu": 2, "cpu": "", "smbios":"", "kvm":"", "sol":"",
                     "disks":"", "networks":""}
        self.vm_templates = {"qemu":"", "disk":"", "net_bridge":"", "net_nat":""}
        self.start_command = ""
        self.vm_templates["qemu"] = "sudo /usr/local/bin/qemu-system-x86_64 -name {name} -boot ncd,menu=on -machine pc-q35-2.5 {cpu} {kvm} -m {memory} -realtime mlock=off -smp {vcpu} -rtc base=utc {smbios} -device ahci,id=sata0 {disks} {networks} -vnc :1 {sol} -chardev socket,id=ipmi0,host=localhost,port=9002,reconnect=10 -device ipmi-bmc-extern,chardev=ipmi0,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0 -cdrom /dev/sr0 &"
        self.vm_templates["disk"] = "-drive file={file},format=qcow2,if=none,id=drive-sata0-0-{idx} -device ide-hd,bus=sata0.0,drive=drive-sata0-0-{idx},id=sata0-0-{idx} "
        self.vm_templates["net_bridge"] = "-net nic,model=e1000,macaddr={mac} -net tap,id=hostnet0,fd={fd} {fd}<>/dev/tap{tap} "
        self.vm_templates["net_nat"] = "-netdev user,id=vnet{id} -device e1000,mac={mac},netdev=vnet{id} "

        #self.set_smbios()

    def __set_default_config(self):
        self.set_kvm_enable()
        self.set_cpu()
        self.set_smbios()
        self.set_network()
        self.set_disks()

    def set_kvm_enable(self):
        output = subprocess.check_output("cat /proc/cpuinfo".split(" "))
        if output.find("vmx") > 0:
            self.vm_features["kvm"] = "--enable-kvm"
        else:
            self.vm_features["kvm"] = ""

    def set_cpu(self, cpu="Haswell"):
        if self.vm_features["kvm"] is not "":
            self.vm_features["cpu"] = "-cpu {},+vmx".format(cpu)
        else:
            self.vm_features["cpu"] = ""

    def set_smbios(self, name="quanta_d51"):
        self.vm_features["smbios"] = "-smbios file=/usr/local/etc/infrasim/{0}/{0}_smbios.bin".format(name)

    def set_memory(self, memory=1024):
        self.vm_features["memory"] = memory

    def set_vcpu(self, vcpu=4):
        self.vm_features["vcpu"] = vcpu

    def set_sol(self):
        self.vm_features["sol"] = "-serial mon:tcp:127.0.0.1:9003,nowait"

    def set_network(self, network="nat"):
        conf = ConfigParser.ConfigParser()
        conf.read(self.VM_DEFAULT_CONFIG)
        macs = []
        if conf.has_option("node", "mac1") is True:
           macs.append(conf.get("node", "mac1"))
        if conf.has_option("node", "mac2") is True:
           macs.append(conf.get("node", "mac2"))
        if conf.has_option("node", "mac3") is True:
           macs.append(conf.get("node", "mac3"))

        for i in range(0, len(macs)):
            if network == "nat":
                self.vm_features["networks"] = self.vm_features["networks"] + self.vm_templates["net_nat"].format(mac=macs[i],id=i)
            if network == "bridge":
                pass

    def set_disks(self):
        conf = ConfigParser.ConfigParser()
        conf.read(self.VM_DEFAULT_CONFIG)
        disk_num = 0
        disk_size = 0
        if conf.has_option("node", "disk_num") is True:
            disk_num = conf.getint("node", "disk_num")
        else:
            print "No disk_count"
            sys.exit(-1)

        if conf.has_option("node", "disk_size") is True:
            disk_size = conf.getint("node", "disk_size")
        else:
            print "No disk_size"
            sys.exit(-1)

        disk_file_base = os.environ['HOME'] + '/.infrasim/'
        for i in range(0, disk_num):
            disk_file = disk_file_base + "sd{0}.img".format(chr(97+i))
            if os.path.exists(disk_file) is True:
                self.vm_features["disks"] = self.vm_features["disks"] + self.vm_templates["disk"].format(file=disk_file, idx=i)
            else:
               command = "qemu-img create -f qcow2 {0}sd{1}.img {2}G".format(disk_file_base, chr(97+i), disk_size)
               os.system(command)
               self.vm_features["disks"] = self.vm_features["disks"] + self.vm_templates["disk"].format(file=disk_file, idx=i)

    def read_from_config(self):
        conf = ConfigParser.ConfigParser()
        conf.read(self.VM_DEFAULT_CONFIG)
        if conf.has_option("main", "node") is True:
            self.vm_features["name"] = conf.get("main", "node")
            self.set_smbios(self.vm_features["name"])
        if conf.has_option("node", "cpu") is True:
            self.set_cpu(conf.get("node", "cpu"))
        if conf.has_option("node", "memory") is True:
            self.set_memory(conf.getint("node", "memory"))
        if conf.has_option("node", "vcpu") is True:
            self.set_vcpu(conf.getint("node", "vcpu"))

        self.set_disks()
        self.set_network()
        self.set_sol()

    def get_qemu_cmd(self):
        cmd = self.vm_templates["qemu"].format(name = self.vm_features["name"], cpu = self.vm_features["cpu"],
                         vcpu = self.vm_features["vcpu"], memory = self.vm_features["memory"],
                         smbios = self.vm_features["smbios"], kvm = self.vm_features["kvm"], sol = self.vm_features["sol"],
                         networks = self.vm_features["networks"], disks = self.vm_features["disks"])
        return cmd

def start_qemu():
    vm = QEMU()
    vm.read_from_config()
    run_command(vm.get_qemu_cmd(), True, None, None)

def stop_qemu():
    qemu_stop_cmd = "pkill qemu"
    run_command(qemu_stop_cmd, True, None, None)
