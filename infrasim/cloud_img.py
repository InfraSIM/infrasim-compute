'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
import string
import random
from infrasim import run_command


# def load_backing_file we can add load backing file from cloud image offical website later

def gen_qemuimg(boot_img):
    status, output = run_command("qemu-img create -f qcow2 -o backing_file=/home/infrasim/jenkins/data/"
                                 "ubuntu-16.04-server-cloudimg-amd64-120G.org.bak cloudimgs/{}".format(boot_img))
    return str(os.getcwd() + "/cloudimgs/") + boot_img


def geniso(myseed_name, instance_id, mac_addr, guest_ip, gate_way, mac1):
    create_network_config_file(mac_addr, guest_ip, gate_way, mac1)
    # instance_id = id_generator(8)+"-"+ id_generator(4)+"-"+id_generator(4)+"-"+id_generator(4)+"-"+id_generator(12)
    # instance_id = "305c9cc1-2f5a-4e76-b28e-ed8313fa283e"
    create_meta_data(instance_id)
    create_user_data()
    status, output = run_command("genisoimage -output cloudimgs/{} -volid cidata -joliet -rock "
                                 "cloudimgs/user-data cloudimgs/meta-data cloudimgs/network-config".format(myseed_name))
    return str(os.getcwd() + "/cloudimgs/") + myseed_name


def clear_files():
    status, output = run_command("sudo rm -rf cloudimgs")
    print "status" + str(status)


def id_generator(size):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(size))


def create_network_config_file(mac_addr, guest_ip, gate_way, mac1):
    script_name = str(os.getcwd()) + "/cloudimgs/network-config"
    script_content = '''---
version: 1
config:
- type: physical
  name: enp0s3
  mac_address: {}
  subnets:
  - type: dhcp
- type: physical
  name: eth0
  mac_address: {}
  subnets:
  - type: static
    address: {}
    netmask: 255.255.255.0
    routes:
    - network: 0.0.0.0
      netmask: 0.0.0.0
      gateway: 192.168.188.1
- type: nameserver
  address: [{}, 8.8.8.8, 8.8.4.4]
  search: [example.com, foo.biz, bar.info]
'''.format(mac1, mac_addr, guest_ip, gate_way)
    status, output = run_command("echo \"{}\" > {}".format(script_content, script_name))
    return script_name


def create_meta_data(instance_id):
    script_name = str(os.getcwd()) + "/cloudimgs/meta-data"
    script_content = '''instance-id: {}
local-hostname: cloud
'''.format(instance_id)
    status, output = run_command("echo \"{}\" > {}".format(script_content, script_name))
    return script_name


def create_user_data():
    script_name = str(os.getcwd()) + "/cloudimgs/user-data"
    script_content = '''#cloud-config

password: password
chpasswd: { expire: False }
ssh_pwauth: True
'''
    status, output = run_command("echo \"{}\" > {}".format(script_content, script_name))
    return script_name
