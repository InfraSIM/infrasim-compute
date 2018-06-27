'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
import string
import random
import yaml
from collections import OrderedDict
import test.fixtures as fixtures
from infrasim import run_command


# def load_backing_file we can add load backing file from cloud image offical website later

def gen_qemuimg(boot_img_path, boot_img):
    status, output = run_command("qemu-img create -f qcow2 -o backing_file={} cloudimgs/{}".format(boot_img_path, boot_img))
    return str(os.getcwd() + "/cloudimgs/") + boot_img


def geniso(myseed_name, instance_id, networkconfig):
    create_meta_data(instance_id)
    create_network_config_file(networkconfig)
    create_user_data()
    status, output = run_command("genisoimage -output cloudimgs/{} -volid cidata -joliet -rock "
                                 "cloudimgs/user-data cloudimgs/meta-data cloudimgs/network-config".format(myseed_name))
    return str(os.getcwd() + "/cloudimgs/") + myseed_name


def clear_files():
    status, output = run_command("sudo rm -rf cloudimgs")
    print "status" + str(status)


def id_generator(size):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(size))


def generate_script_content(networkconfig):
    yaml.add_representer(fixtures.FlowList, lambda dumper, data: dumper.represent_sequence(u'tag:yaml.org,2002:seq',
                                                                                           data, flow_style=True))
    yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_mapping(u'tag:yaml.org,2002:map',
                                                                                    data.items()))

    network_config_yaml = yaml.dump(networkconfig, default_flow_style=False)
    return network_config_yaml


def create_network_config_file(networkconfig):
    """
    sample network config:
        version: 1
        config:
        - type: physical
          name: enp0s3
          mac_address: 00:60:16:93:b9:2a
          subnets:
          - type: dhcp
        - type: physical
          name: eth0
          mac_address: 00:60:16:93:b9:1d
          subnets:
          - type: static
            address: 192.168.188.12
            netmask: 255.255.255.0
            routes:
            - network: 0.0.0.0
              netmask: 0.0.0.0
              gateway: 192.168.188.1
        - type: nameserver
          address: [192.168.188.1, 8.8.8.8, 8.8.4.4]
          search: [example.com, foo.biz, bar.info]
    """
    script_name = str(os.getcwd()) + "/cloudimgs/network-config"
    script_content = generate_script_content(networkconfig)
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
