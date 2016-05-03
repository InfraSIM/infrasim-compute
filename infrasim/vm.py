#!/usr/bin/env python
# -*- coding: utf-8 -*-

import jinja2, uuid, ConfigParser
import libvirt

class VM:
    def __init__(self, node_name, xml_file):
        self.node = {"name":node_name, "uuid":str(uuid.uuid1()), 
                   "virtual_type":"qemu", "mem_size":512, "vcpu_num":4, "vcpu_type":"Haswell"}
        self.xml_file = xml_file
        self.render_xml = ""
        self.set_sata_disks(1)
        self.set_mac_address()

    def set_virtual_type(self):
        self.node["virtual_type"] = "qemu"

    def set_memory_size(self):
        self.node["mem_size"] = 512

    def set_vcpu_num(self):
        self.node["vcpu_num"] = 4

    def set_vcpu_type(self):
        self.node["vcpu_type"] = "Haswell"

    def set_sata_disks(self, disk_num):
        disks = []
        for i in range(0, disk_num):
            disk = {"file":"/usr/local/etc/infrasim/cirros-0.3.4-x86_64-disk.img",
                   "dev":"sd" + chr(97+i), "name":"sata0-0-" + str(i)}
            disks.append(disk)
        self.node["disks"] = disks

    def set_sata_disks_with_size(self, disk_num, disk_size):
        disks = []
        for i in range(0, disk_num):
            disk = {"file":"/usr/local/etc/infrasim/cirros-0.3.4-x86_64-disk.img",
                    "dev":"sd" + chr(97+i), "name":"sata0-0-" + str(i)}
            disks.append(disk)
        self.node["disks"] = disks

    def set_mac_address(self):
        nets = []
        nets.append({"mac":"52:54:00:ad:66:b5"})
        self.node["nets"] = nets

    def read_from_config(self, config_file):
        conf = ConfigParser.ConfigParser()
        conf.read(config_file)
        if conf.has_option("node", "mem_size") is True:
            self.node["mem_size"] = conf.getint("node", "mem_size")
        elif conf.has_option("node", "vcpu_num") is True:
            self.node["vcpu_num"] = conf.getint("node", "vcpu_num")
        elif conf.has_option("node", "vcpu_type") is True:
            self.node["vcpu_type"] = conf.get("node", "vcpu_type")
        elif conf.has_option("node", "disk_num") is True:
            if conf.has_option("node", "disk_size") is True:
                disk_num = conf.getint("node", "disk_num")
                disk_size = conf.getint("node", "disk_size")
                self.set_sata_disks_with_size(disk_num, disk_size)
            else:
                disk_num = conf.getint("node", "disk_num")
                self.set_sata_disks(disk_num)
        else:
            pass
        
    def render_vm_template(self):
        raw_xml = ""
        with open(self.xml_file, 'r') as f:
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
