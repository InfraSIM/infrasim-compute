#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, uuid, subprocess, ConfigParser, sys, socket, time
import netifaces
from . import run_command, logger, CommandNotFound, CommandRunFailed

def get_qemu():
    try:
        code, qemu_cmd = run_command("which /usr/local/bin/qemu-system-x86_64")
        return qemu_cmd.strip(os.linesep)
    except CommandRunFailed as e:
        raise CommandNotFound("/usr/local/bin/qemu-system-x86_64")

def status_qemu():
    try:
        run_command("pidof qemu-system-x86_64")
        print "Infrasim Qemu service is running"
    except CommandRunFailed as e:
        print "Inrasim Qemu service is stopped"

def create_macvtap(idx, nic, mac):
    run_command("ip link add link {} name macvtap{} type macvtap mode bridge".format(nic, idx))
    run_command("ip link set macvtap{} address {} up".format(idx, mac))
    run_command("ifconfig macvtap{} promisc".format(idx))
    time.sleep(1)

def stop_macvtap(eth):
    run_command("ip link set {} down".format(eth))
    run_command("ip link delete {}".format(eth))

class QEMU():
    VM_DEFAULT_CONFIG = "/etc/infrasim/infrasim.conf"
    def __init__(self):
        self.vm_features = {"name": "quanta_d51", "memory": 1024,
                     "vcpu": 2, "cpu": "", "smbios":"", "kvm":"", "sol":"",
                     "disks":"", "networks":""}
        self.vm_templates = {"qemu":"", "disk":"", "net_macvtap":"", "net_nat":""}
        self.start_command = ""
        self.vm_templates["qemu"] = "/usr/local/bin/qemu-system-x86_64 -name {name} -boot ncd,menu=on -machine pc-q35-2.5 {cpu} {kvm} -m {memory} -realtime mlock=off -smp {vcpu} -rtc base=utc {smbios} -device ahci,id=sata0 {disks} {networks} -vnc :1 {sol} -chardev socket,id=ipmi0,host=localhost,port=9002,reconnect=10 -device ipmi-bmc-extern,chardev=ipmi0,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0 -chardev socket,id=mon,host=127.0.0.1,port=2345,server,nowait -mon chardev=mon,id=monitor  -cdrom /dev/sr0 2>/var/tmp/qemu.log"
        self.vm_templates["disk"] = "-drive file={file},format=qcow2,if=none,id=drive-sata0-0-{idx} -device ide-hd,bus=sata0.0,drive=drive-sata0-0-{idx},id=sata0-0-{idx} "
        self.vm_templates["net_macvtap"] = "-device e1000,mac={mac},netdev=hostnet{idx} -netdev tap,id=hostnet{idx},fd={fd} {fd}<>/dev/tap{tap} "
        self.vm_templates["net_nat"] = "-net user -net nic"
        self.set_kvm_enable()

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
        pass
        #self.vm_features["sol"] = "-serial mon:tcp:127.0.0.1:9003,nowait"

    def set_network(self):
        conf = ConfigParser.ConfigParser()
        conf.read(self.VM_DEFAULT_CONFIG)
        macs = []
        mode = ""
        eth_name = ""
        if conf.has_option("node", "network_mode") is True:
           mode = conf.get("node", "network_mode")

        if mode == "nat":
            self.vm_features["networks"] = self.vm_templates["net_nat"]
            return

        eth_name = conf.get("node", "network_name")
        if conf.has_option("node", "network_mac1") is True:
           macs.append(conf.get("node", "network_mac1"))
        if conf.has_option("node", "network_mac2") is True:
           macs.append(conf.get("node", "network_mac2"))
        if conf.has_option("node", "network_mac3") is True:
           macs.append(conf.get("node", "network_mac3"))

        for i in range(0, len(macs)):
            create_macvtap(i, eth_name, macs[i])
            mac = subprocess.check_output("cat /sys/class/net/macvtap{}/address".format(i), shell=True).strip()
            tap = subprocess.check_output("cat /sys/class/net/macvtap{}/ifindex".format(i), shell=True).strip()
            self.vm_features["networks"] = self.vm_features["networks"] + self.vm_templates["net_macvtap"].format(mac=mac, tap = tap, idx=i, fd=(i+3))

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
               run_command(command)
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
    cmd = vm.get_qemu_cmd()
    logger.debug(cmd)
    try:
        run_command(cmd, True, None, None)
        logger.info("qemu start")
    except CommandRunFailed as e:
        raise e

def stop_qemu():
    nics_list = netifaces.interfaces()
    macvtaps = filter(lambda x: 'macvtap' in x,nics_list)
    for vtaps in macvtaps:
        stop_macvtap(vtaps)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1",  2345))
        sock.send("quit\n")
        sock.close()
    except Exception, e:
        pass
    logger.info("qemu stopped")
