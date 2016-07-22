#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, uuid, subprocess, ConfigParser, sys, socket, time
import netifaces
from . import run_command, logger, CommandNotFound, CommandRunFailed, ArgsNotCorrect

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
    try:
        run_command("ip link add link {} name macvtap{} type macvtap mode bridge".format(nic, idx))
        run_command("ip link set macvtap{} address {} up".format(idx, mac))
        run_command("ifconfig macvtap{} promisc".format(idx))
        time.sleep(1)
    except CommandRunFailed as e:
        raise e

def stop_macvtap(eth):
    try:
        run_command("ip link set {} down".format(eth))
        run_command("ip link delete {}".format(eth))
    except CommandRunFailed as e:
        raise e

class QEMU():
    VM_DEFAULT_CONFIG = "/etc/infrasim/infrasim.conf"
    def __init__(self):
        self.vm_features = {"name": "quanta_d51", "memory": 1024,
                     "vcpu": 2, "cpu": "", "smbios":"", "kvm":"", "sol":"",
                     "disks":"", "networks":"", "cdrom":""}
        self.vm_templates = {"qemu":"", "disk":"", "net_macvtap":"", "net_nat":""}
        self.start_command = ""
        self.vm_templates["qemu"] = "/usr/local/bin/qemu-system-x86_64 -name {name} -boot ncd,menu=on -machine pc-q35-2.5 {cpu} {kvm} -m {memory} -realtime mlock=off -smp {vcpu} -rtc base=utc {smbios} -device sga -device ahci,id=sata0 {disks} {networks} -vnc :1 {sol} -chardev socket,id=ipmi0,host=localhost,port=9002,reconnect=10 -device ipmi-bmc-extern,chardev=ipmi0,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0 -chardev socket,id=mon,host=127.0.0.1,port=2345,server,nowait -mon chardev=mon,id=monitor {cdrom} 2>/var/tmp/qemu.log &"
        self.vm_templates["disk"] = "-drive file={file},format=qcow2,if=none,id=drive-sata0-0-{idx} -device ide-hd,bus=sata0.0,drive=drive-sata0-0-{idx},id=sata0-0-{idx} "
        self.vm_templates["net_macvtap"] = "-device e1000,mac={mac},netdev=hostnet{idx} -netdev tap,id=hostnet{idx},fd={fd} {fd}<>/dev/tap{tap} "
        self.vm_templates["net_nat"] = "-net user -net nic"
        self.set_kvm_enable()

    def set_kvm_enable(self):
        if os.path.exists("/dev/kvm") is True:
            self.vm_features["kvm"] = "--enable-kvm"
        else:
            self.vm_features["kvm"] = ""

    def set_node(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)
        if conf.has_option("main", "node") is True:
            self.vm_features["name"] = conf.get("main", "node")
            self.vm_features["smbios"] = "-smbios file=/usr/local/etc/infrasim/{0}/{0}_smbios.bin".format(conf.get("main", "node"))
        else:
            raise ArgsNotCorrect("parameter: node is not found")

    def set_cpu(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)

        if conf.has_option("node", "cpu") is True:
            if self.vm_features["kvm"] is not "":
                self.vm_features["cpu"] = "-cpu {},+vmx".format(conf.get("node", "cpu"))
            else:
                self.vm_features["cpu"] = ""
        else:
            raise ArgsNotCorrect("parameter: cpu is not found")

    def set_memory(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)

        if conf.has_option("node", "memory") is True:
            self.vm_features["memory"] = conf.getint("node", "memory")
        else:
            raise ArgsNotCorrect("parameter: memory is not found")

    def set_vcpu(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)

        if conf.has_option("node", "vcpu") is True:
            self.vm_features["vcpu"] = conf.getint("node", "vcpu")
        else:
            raise ArgsNotCorrect("parameter: vcpu is not found")

    def set_sol(self):
        self.vm_features["sol"] = "-serial mon:tcp:127.0.0.1:9003,nowait"

    def set_network(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)
        macs = []
        mode = ""
        eth_name = ""
        if conf.has_option("node", "network_mode") is True:
           mode = conf.get("node", "network_mode")
        else:
           raise ArgsNotCorrect("parameter: network_mode is not found")

        if mode == "nat":
            self.vm_features["networks"] = self.vm_templates["net_nat"]
            return
        elif mode == "macvtap":
            if conf.has_option("node", "network_name") is True:
                eth_name = conf.get("node", "network_name")
            else:
                raise ArgsNotCorrect("parameter: network_name is not found")

            if conf.has_option("node", "network_mac1") is True:
               macs.append(conf.get("node", "network_mac1"))
            if conf.has_option("node", "network_mac2") is True:
               macs.append(conf.get("node", "network_mac2"))
            if conf.has_option("node", "network_mac3") is True:
               macs.append(conf.get("node", "network_mac3"))

            if len(macs) == 0:
               raise ArgsNotCorrect("No network mac address found")

            try:
                for i in range(0, len(macs)):
                    create_macvtap(i, eth_name, macs[i])
                    mac = subprocess.check_output("cat /sys/class/net/macvtap{}/address".format(i), shell=True).strip()
                    tap = subprocess.check_output("cat /sys/class/net/macvtap{}/ifindex".format(i), shell=True).strip()
                    self.vm_features["networks"] = self.vm_features["networks"] + self.vm_templates["net_macvtap"].format(mac=mac, tap = tap, idx=i, fd=(i+3))
            except CommandRunFailed as e:
                raise CommandRunFailed("Create macvtap failed, please check your ethname setting")
        else:
            raise ArgsNotCorrect("Not supported network mode {}".format(mode))

    def set_disks(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)
        disk_num = 0
        disk_size = 0
        if conf.has_option("node", "disk_num") is True:
            disk_num = conf.getint("node", "disk_num")
        else:
            raise ArgsNotCorrect("parameter: disk_num is not found")

        if conf.has_option("node", "disk_size") is True:
            disk_size = conf.getint("node", "disk_size")
        else:
            raise ArgsNotCorrect("parameter: disk_size is not found")

        disk_file_base = os.environ['HOME'] + '/.infrasim/'
        for i in range(0, disk_num):
            disk_file = disk_file_base + "sd{0}.img".format(chr(97+i))
            if os.path.exists(disk_file) is True:
                self.vm_features["disks"] = self.vm_features["disks"] + self.vm_templates["disk"].format(file=disk_file, idx=i)
            else:
               command = "qemu-img create -f qcow2 {0}sd{1}.img {2}G".format(disk_file_base, chr(97+i), disk_size)
               try:
                   run_command(command)
                   self.vm_features["disks"] = self.vm_features["disks"] + self.vm_templates["disk"].format(file=disk_file, idx=i)
               except CommandRunFailed as e:
                   raise e

    def set_cdrom(self, config_file):
        if os.path.exists("/dev/sr0") is True:
            self.vm_features["cdrom"] = "-cdrom /dev/sr0"

        conf = ConfigParser.ConfigParser()
        conf.read(config_file)
        if conf.has_option("node", "cdrom") is True:
            self.vm_features["cdrom"] = "-cdrom " + conf.get("node", "cdrom")

    def read_from_config(self, config_file):
        try:
            self.set_node(config_file)
            self.set_cpu(config_file)
            self.set_memory(config_file)
            self.set_vcpu(config_file)
            self.set_disks(config_file)
            self.set_network(config_file)
            self.set_sol()
            self.set_cdrom(config_file)
        except CommandRunFailed as e:
            raise e
        except ArgsNotCorrect as e:
            raise e

    def get_qemu_cmd(self):
        cmd = self.vm_templates["qemu"].format(name = self.vm_features["name"], cpu = self.vm_features["cpu"],
                         vcpu = self.vm_features["vcpu"], memory = self.vm_features["memory"],
                         smbios = self.vm_features["smbios"], kvm = self.vm_features["kvm"], sol = self.vm_features["sol"],
                         networks = self.vm_features["networks"], disks = self.vm_features["disks"], cdrom=self.vm_features["cdrom"])
        return cmd

def start_qemu():
    vm = QEMU()
    try:
        vm.read_from_config(vm.VM_DEFAULT_CONFIG)
        cmd = vm.get_qemu_cmd()
        logger.debug(cmd)
        run_command(cmd, True, None, None)
        logger.info("qemu start")
    except CommandRunFailed as e:
        logger.error(e.value)
        raise e
    except ArgsNotCorrect as e:
        logger.error(e.value)
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
