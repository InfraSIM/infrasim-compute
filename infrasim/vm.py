#!/usr/bin/env python
# -*- coding: utf-8 -*-

import jinja2, uuid, ConfigParser, subprocess, os
import libvirt, logging

VM_DEFAULT_CONFIG="/etc/infrasim/infrasim.conf"
VM_DEFAULT_XML="/usr/local/etc/infrasim/vnode.xml"

class VM:
    def __init__(self):
        self.node = {"name":"quanta_d51", "uuid":str(uuid.uuid1()), "bios":{},
                   "virtual_type":"qemu", "mem_size":512, "vcpu_num":4, "vcpu_type":"Haswell"}
        self.render_xml = ""
        self.logger = logging.getLogger('infrasim')
        self.set_virtual_type()
        self.set_bios_data(self.node["name"])
        self.set_sata_disks(1)
        self.set_network("nat", None)
        if os.path.exists(os.environ['HOME'] + '/.infrasim') is False:
            os.mkdir(os.environ['HOME'] + "/.infrasim")

    def set_virtual_type(self):
        output = subprocess.check_output("cat /proc/cpuinfo".split(" "))
        if output.find("vmx") > 0:
            self.node["virtual_type"] = "kvm"

    def set_bios_data(self, node):
        bios = {"bios":{}, "system":{}, "base":{}}
        bios_file = "/usr/local/etc/infrasim/{0}/{0}_smbios.bin".format(node)
        bios["bios"]["vendor"]=subprocess.check_output("dmidecode --from-dump {0} -s bios-vendor".format(bios_file).split(" "))
        bios["system"]["manufacturer"] = subprocess.check_output("dmidecode --from-dump {0} -s system-manufacturer".format(bios_file).split(" "))
        bios["system"]["product"] = subprocess.check_output("dmidecode --from-dump {0} -s system-product-name".format(bios_file).split(" "))
        bios["system"]["version"] = subprocess.check_output("dmidecode --from-dump {0} -s system-version".format(bios_file).split(" "))
        bios["base"]["manufacturer"] = subprocess.check_output("dmidecode --from-dump {0} -s baseboard-manufacturer".format(bios_file).split(" "))
        bios["base"]["product"]=subprocess.check_output("dmidecode --from-dump {0} -s baseboard-product-name".format(bios_file).split(" "))
        bios["base"]["version"] = subprocess.check_output("dmidecode --from-dump {0} -s baseboard-version".format(bios_file).split(" "))
        bios["base"]["serial"] = subprocess.check_output("dmidecode --from-dump {0} -s baseboard-serial-number".format(bios_file).split(" "))
        self.node["bios"] = bios

    def set_memory_size(self):
        self.node["mem_size"] = 512

    def set_vcpu_num(self):
        self.node["vcpu_num"] = 4

    def set_vcpu_type(self):
        self.node["vcpu_type"] = "Haswell"

    def set_pxe(self):
        self.node["pxe"] = "{0}\n{1}\n{2}\n".format("<kernel>/var/www/html/CentOS/7.0/images/pxeboot/vmlinuz</kernel>",
    			"<initrd>/var/www/html/CentOS/7.0/images/pxeboot/initrd.img</initrd>",
                        "<cmdline>ks=http://192.168.191.133/kickstart/centos-ks.cfg</cmdline>")

    def create_disk_image(self, disk_idx, disk_size=4):
        disk_dir = os.environ['HOME'] + "/.infrasim"
        disk_img = "sd{0}.img".format(chr(97+disk_idx))
        if os.path.isfile(disk_dir + disk_img) is True:
            if disk_size != 4:
                os.remove(disk_dir + disk_img)
            else:
                return

        command = "qemu-img create -f qcow2 {0}{1} {2}G".format(disk_dir, disk_img, disk_size)
        os.system(command)

    def set_sata_disks(self, disk_num):
        disk_dir = os.environ['HOME'] + "/.infrasim"
        disks = []
        for i in range(0, disk_num):
            self.create_disk_image(i)
            disk = {"file":"{0}sd{1}.img".format(disk_dir, chr(97+i)),
                   "dev":"sd" + chr(97+i), "name":"sata0-0-" + str(i)}
            disks.append(disk)
        self.node["disks"] = disks

    def set_sata_disks_with_size(self, disk_num, disk_size):
        disk_dir = os.environ['HOME'] + "/.infrasim"
        disks = []
        for i in range(0, disk_num):
            self.create_disk_image(i, disk_size)
            disk = {"file":"{0}sd{1}.img".format(disk_dir, chr(97+i)),
                    "dev":"sd" + chr(97+i), "name":"sata0-0-" + str(i)}
            disks.append(disk)
        self.node["disks"] = disks

    def set_network(self, mode, name):
        nets = []
        if mode == "nat":
            self.node["netmode"] = "nat"
            nets.append({"mac":"52:54:00:ad:66:b5"})
        else:
            self.node["netmode"] = "brdige"
            nets.append({"mac":"52:54:00:ad:66:b5", "dev":name})
        self.node["nets"] = nets

    def read_from_config(self):
        conf = ConfigParser.ConfigParser()
        conf.read(VM_DEFAULT_CONFIG)
        if conf.has_option("main", "node") is True:
            self.node["name"] = conf.get("main", "node")
        if conf.has_option("node", "mem_size") is True:
            self.node["mem_size"] = conf.getint("node", "mem_size")
        if conf.has_option("node", "vcpu_num") is True:
            self.node["vcpu_num"] = conf.getint("node", "vcpu_num")
        if conf.has_option("node", "vcpu_type") is True:
            self.node["vcpu_type"] = conf.get("node", "vcpu_type")
        if conf.has_option("node", "pxeboot") is True:
            if conf.get("node", "pxeboot") == "yes":
                self.set_pxe()
        if conf.has_option("node", "disk_num") is True:
            if conf.has_option("node", "disk_size") is True:
                disk_num = conf.getint("node", "disk_num")
                disk_size = conf.getint("node", "disk_size")
                self.set_sata_disks_with_size(disk_num, disk_size)
            else:
                disk_num = conf.getint("node", "disk_num")
                self.set_sata_disks(disk_num)
        if conf.has_option("node", "disk_size") is True:
            disk_num = conf.getint("node", "disk_num")
            self.set_sata_disks(disk_num)
        if conf.has_option("node", "network_mode") is True:
            nm = conf.get("node", "network_mode")
            bridge = ""
            if nm == "bridge":
                bridge = conf.get("node", "network_name")
            self.set_network(nm, bridge)
        
        self.set_bios_data(self.node["name"])

    def render_vm_template(self):
        raw_xml = ""
        with open(VM_DEFAULT_XML, 'r') as f:
            raw_xml = f.read()
        template = jinja2.Template(raw_xml)
        self.render_xml = template.render(node = self.node)
        return self.render_xml

def start_vm(vm_desc):
    conn =libvirt.open()
    conn.createLinux(vm_desc, 0)
    conn.close()

def stop_vm(node):
    conn = libvirt.open()
    domain = conn.lookupByName(node)

    domain.destroy()
    conn.close()

def status_vm(node):
    conn = libvirt.open()
    domainIDs = conn.listDomainsID()
    for id in domainIDs:
        domain = conn.lookupByID(id)
        if domain.name() == node:
            conn.close()
            return True
    return False

def check_vm_status(node):
    conn = libvirt.open()
    vm_exist_flag = False

    domainIDs = conn.listDomainsID()
    if len(domainIDs) == 1:
        domain = conn.lookupByID(domainIDs[0])
        if domain.name() == node:
            vm_exist_flag = True
        else:
           domain.destroy()
           vm_exist_flag = False
    elif len(domainIDs) > 1:
        for id in domainIDs:
            domain = conn.lookupByID(id)
            if domain.name() != node:
                domain.destroy()
            elif domain.name() == node:
                vm_exist_flag = True
            else:
                pass
    else:
        pass

    conn.close()
    return vm_exist_flag
