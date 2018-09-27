#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import re
import unittest
from test import fixtures
import yaml
from infrasim import config
from infrasim import model
from infrasim import helper
from infrasim import run_command
from infrasim.sshclient import SSH

"""
SAS controllers type includes:
    - AHCI controller
    - LSI SAS controller
    - Mega SAS controller
"""

# tmp yaml file for test.
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)

test_img_file = "/home/infrasim/jenkins/data/ubuntu16.04.qcow2"

drive2 = [{"size": 8, "file": "/tmp/sda.img"},
          {"size": 16, "file": "/tmp/sdb.img"}]

drive6 = [{"size": 8, "file": "/tmp/sda.img"},
          {"size": 16, "file": "/tmp/sdb.img"},
          {"size": 8, "file": "/tmp/sdc.img"},
          {"size": 16, "file": "/tmp/sdd.img"},
          {"size": 8, "file": "/tmp/sde.img"},
          {"size": 16, "file": "/tmp/sdf.img"}]


def get_qemu_pid(node):
    for t in node.get_task_list():
        if isinstance(t, model.CCompute):
            return t.get_task_pid()
    return None


def set_port_forward_try_ssh(node):
    import time
    helper.port_forward(node)
    ssh = helper.prepare_ssh()
    ssh.close()
    time.sleep(5)


def get_storage_list():
    storage_list = []
    ssh = SSH("127.0.0.1", "root", "root", port=2222)
    assert ssh.wait_for_host_up() is True

    status, output = ssh.exec_command("which lsscsi")
    assert status == 0

    status, output = ssh.exec_command("lsscsi -t -H")
    print output
    assert status == 0
    for c in output.strip().split(os.linesep):
        c_obj = re.search('\[(?P<bus>\d+)\]\s+(?P<controller>\w+)\s?.*:?', c)
        if c_obj is None:
            continue

        c_name = c_obj.groupdict().get('controller')
        c_bus = c_obj.groupdict().get('bus')

        assert c_name and c_bus
        # map should be as below for example:
        # {'name': 'ahci', 'buses': [], 'disks':[]}
        controller_map = {}
        for c_map in storage_list:
            if c_map and c_name == c_map['name']:
                controller_map = c_map
                break

        if controller_map:
            if c_bus not in controller_map["buses"] and controller_map['name'] == c_name:
                controller_map["buses"].append(c_bus)
        else:
            # initialize map, and and it to storage_list
            controller_map['name'] = c_name
            controller_map["buses"] = []
            controller_map["disks"] = []
            controller_map["buses"].append(c_bus)
            storage_list.append(controller_map)

    status, output = ssh.exec_command("lsscsi -pgw")
    assert status == 0
    print output
    for d in output.strip().split(os.linesep):
        d_obj = re.search('\[(?P<bus>\d+):\d+:\d+:\d+\]\s+disk.*\s+(?P<device_name>\/dev\/sd\w+)\s+.*', d)
        if d_obj is None:
            continue

        bus = d_obj.groupdict().get('bus')
        device_name = d_obj.groupdict().get('device_name')
        assert bus and device_name
        for c_map in storage_list:
            if bus in c_map['buses']:
                assert device_name not in c_map['disks']
                c_map['disks'].append(device_name)
    return storage_list


class test_ahci_controller_with_two_drives(unittest.TestCase):

    @classmethod
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for drive in drive2:
            if os.path.exists(drive["file"]):
                os.unlink(drive["file"])

    def test_controller_with_drive2(self):
        # Update ahci controller with two drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": drive2
            }]
        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type = run_command("infrasim node info {} | grep -c ahci".
                                      format(self.conf["name"]))
        self.assertEqual(int(controller_type[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline


class test_megasas_controller_with_two_drives(unittest.TestCase):

    @classmethod
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for drive in drive2:
            if os.path.exists(drive["file"]):
                os.unlink(drive["file"])

    def test_controller_with_drive2(self):
        # Update megasas controller with two drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "megasas",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": drive2
            }]

        self.conf['compute']['storage_backend'].insert(0,
                                                       {
                                                           "type": "ahci",
                                                           "max_drive_per_controller": 6,
                                                           "drives": [
                                                                {
                                                                    'file': fixtures.image,
                                                                    'bootindex': 1,
                                                                    'use_msi': 'true',
                                                                    'size': 8
                                                                }
                                                            ]
                                                       })
        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type = run_command("infrasim node info {} | grep -c megasas".
                                      format(self.conf["name"]))
        self.assertEqual(int(controller_type[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline

        storage_list = get_storage_list()
        megasas_info = None
        for c_map in storage_list:
            if c_map.get('name') == 'megaraid_sas':
                megasas_info = c_map
                break
        assert megasas_info
        assert len(megasas_info.get('disks')) == 2


class test_lsi_controller_with_two_drives(unittest.TestCase):

    @classmethod
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for drive in drive2:
            if os.path.exists(drive["file"]):
                os.unlink(drive["file"])

    def test_controller_with_drive2(self):
        # Update lsi controller with two drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "lsi",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": drive2
            }]

        self.conf['compute']['storage_backend'].insert(0,
                                                       {
                                                           "type": "ahci",
                                                           "max_drive_per_controller": 6,
                                                           "drives": [
                                                                {
                                                                    'file': fixtures.image,
                                                                    'bootindex': 1,
                                                                    'use_msi': 'true',
                                                                    'size': 8
                                                                }
                                                            ]
                                                       })

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)

        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type = run_command("infrasim node info {} | grep -c lsi".
                                      format(self.conf["name"]))
        self.assertEqual(int(controller_type[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline

        storage_list = get_storage_list()
        lsi_info = None
        for c_map in storage_list:
            if c_map.get('name') == 'sym53c8xx':
                lsi_info = c_map
                break
        assert lsi_info
        assert len(lsi_info.get('disks')) == 2


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_ahci_controller_with_more_than_six_drives(unittest.TestCase):

    drives7 = [{"size": 8, "file": "/tmp/sda.img"},
               {"size": 16, "file": "/tmp/sdb.img"},
               {"size": 8, "file": "/tmp/sdc.img"},
               {"size": 16, "file": "/tmp/sdd.img"},
               {"size": 8, "file": "/tmp/sde.img"},
               {"size": 16, "file": "/tmp/sdf.img"},
               {"size": 8, "file": "/tmp/sdg.img"}]

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for i in range(97, 108):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_controller_with_drive7(self):
        # Update ahci controller with seven drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": self.drives7
            }]
        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        controller_type_ahci = run_command("infrasim node info {} | grep -c ahci".
                                           format(self.conf["name"]))
        self.assertEqual(int(controller_type_ahci[1]), 2)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "/tmp/sdc.img" in qemu_cmdline
        assert "/tmp/sdd.img" in qemu_cmdline
        assert "/tmp/sde.img" in qemu_cmdline
        assert "/tmp/sdf.img" in qemu_cmdline
        assert "/tmp/sdg.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline
        assert "-device ahci,id=sata1" in qemu_cmdline
        assert "-device ahci,id=sata0" in qemu_cmdline
        assert "drive=sata0-0-5-0" in qemu_cmdline
        assert "drive=sata1-0-0-0" in qemu_cmdline

    def test_controller_with_drive7_drive2_drive3(self):
        # Update ahci controller with seven drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": self.drives7
            }]

        controllers = []
        controllers.append({
            'type': 'ahci',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        controllers.append({
            'type': 'ahci',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        self.conf['compute']['storage_backend'].extend(controllers)

        drives2 = []
        drives2.append({'size': 8, 'file': "/tmp/sdh.img"})
        drives2.append({'size': 16, 'file': "/tmp/sdi.img"})

        self.conf['compute']['storage_backend'][1]['drives'].extend(drives2)

        drives3 = []
        drives3.append({'size': 8, 'file': "/tmp/sdj.img"})
        drives3.append({'size': 16, 'file': "/tmp/sdk.img"})
        drives3.append({'size': 8, 'file': "/tmp/sdl.img"})
        self.conf['compute']['storage_backend'][2]['drives'].extend(drives3)
        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        controller_type_ahci = run_command("infrasim node info {} | grep -c ahci".
                                           format(self.conf["name"]))
        self.assertEqual(int(controller_type_ahci[1]), 4)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "/tmp/sdc.img" in qemu_cmdline
        assert "/tmp/sdd.img" in qemu_cmdline
        assert "/tmp/sde.img" in qemu_cmdline
        assert "/tmp/sdf.img" in qemu_cmdline
        assert "/tmp/sdg.img" in qemu_cmdline
        assert "/tmp/sdh.img" in qemu_cmdline
        assert "/tmp/sdi.img" in qemu_cmdline
        assert "/tmp/sdj.img" in qemu_cmdline
        assert "/tmp/sdk.img" in qemu_cmdline
        assert "/tmp/sdl.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline
        assert "-device ahci,id=sata0" in qemu_cmdline
        assert "-device ahci,id=sata1" in qemu_cmdline
        assert "-device ahci,id=sata2" in qemu_cmdline
        assert "-device ahci,id=sata3" in qemu_cmdline
        assert "drive=sata0-0-5-0" in qemu_cmdline
        assert "drive=sata1-0-0-0" in qemu_cmdline
        assert "drive=sata2-0-1-0" in qemu_cmdline
        assert "drive=sata3-0-2-0" in qemu_cmdline


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_ahci_controller_with_six_drives(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for i in range(97, 102):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_controller_with_drive6(self):
        # Update ahci controller with six drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": drive6
            }]
        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        controller_type = run_command("infrasim node info {} | grep -c ahci".
                                      format(self.conf["name"]))
        self.assertEqual(int(controller_type[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "/tmp/sdc.img" in qemu_cmdline
        assert "/tmp/sdd.img" in qemu_cmdline
        assert "/tmp/sde.img" in qemu_cmdline
        assert "/tmp/sdf.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_megasas_controller_with_six_drives(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for i in range(97, 102):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_controller_with_drive6(self):
        # Update megasas controller with six drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "megasas",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": drive6
            }]

        self.conf['compute']['storage_backend'].insert(0,
                                                       {
                                                           "type": "ahci",
                                                           "max_drive_per_controller": 6,
                                                           "drives": [
                                                                {
                                                                    'file': fixtures.image,
                                                                    'bootindex': 1,
                                                                    'use_msi': 'true',
                                                                    'size': 8
                                                                }
                                                            ]
                                                       })

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type = run_command("infrasim node info {} | grep -c megasas".
                                      format(self.conf["name"]))
        self.assertEqual(int(controller_type[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "/tmp/sdc.img" in qemu_cmdline
        assert "/tmp/sdd.img" in qemu_cmdline
        assert "/tmp/sde.img" in qemu_cmdline
        assert "/tmp/sdf.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline

        storage_list = get_storage_list()
        megasas_info = None
        for c_map in storage_list:
            if c_map.get('name') == 'megaraid_sas':
                megasas_info = c_map
                break
        assert megasas_info
        assert len(megasas_info.get('disks')) == 6


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_lsi_controller_with_six_drives(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for i in range(97, 102):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_controller_with_drive6(self):
        # Update lsi controller with six drives
        self.conf["compute"]["storage_backend"] = [{
            "type": "lsi",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": drive6
            }]

        self.conf['compute']['storage_backend'].insert(0,
                                                       {
                                                           "type": "ahci",
                                                           "max_drive_per_controller": 6,
                                                           "drives": [
                                                                {
                                                                    'file': fixtures.image,
                                                                    'bootindex': 1,
                                                                    'use_msi': 'true',
                                                                    'size': 8
                                                                }
                                                            ]
                                                       })

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        os.system("infrasim config add test {}".format(tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type = run_command("infrasim node info {} | grep -c lsi".
                                      format(self.conf["name"]))
        self.assertEqual(int(controller_type[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "/tmp/sda.img" in qemu_cmdline
        assert "/tmp/sdb.img" in qemu_cmdline
        assert "/tmp/sdc.img" in qemu_cmdline
        assert "/tmp/sdd.img" in qemu_cmdline
        assert "/tmp/sde.img" in qemu_cmdline
        assert "/tmp/sdf.img" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline

        storage_list = get_storage_list()
        lsi_info = None
        for c_map in storage_list:
            if c_map.get('name') == 'sym53c8xx':
                lsi_info = c_map
                break
        assert lsi_info
        assert len(lsi_info.get('disks')) == 6


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_three_storage_controllers(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for i in range(97, 114):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_three_controllers_each_with_six_drives(self):

        image_path = "{}/{}".format(config.infrasim_home, self.conf["name"])
        # Add several storage controllers/drives in node config file.
        drives = []
        drives.append({'size': 16, 'file': "{}/sdb.img".format(image_path)})
        drives.append({'size': 8, 'file': "{}/sdc.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sdd.img".format(image_path)})
        drives.append({'size': 8, 'file': "{}/sde.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sdf.img".format(image_path)})
        self.conf['compute']['storage_backend'][0]['drives'].extend(drives)
        self.conf['compute']['storage_backend'][0]['drives'][0]['file'] = fixtures.image

        controllers = []
        controllers.append({
            'type': 'megasas',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
            })
        controllers.append({
            'type': 'lsi',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
            })
        self.conf['compute']['storage_backend'].extend(controllers)

        drives1 = []
        drives1.append({'size': 8, 'file': "{}/sdg.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdh.img".format(image_path)})
        drives1.append({'size': 8, 'file': "{}/sdi.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdj.img".format(image_path)})
        drives1.append({'size': 8, 'file': "{}/sdk.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdl.img".format(image_path)})
        self.conf['compute']['storage_backend'][1]['drives'].extend(drives1)

        drives2 = []
        drives2.append({'size': 8, 'file': "{}/sdm.img".format(image_path)})
        drives2.append({'size': 16, 'file': "{}/sdn.img".format(image_path)})
        drives2.append({'size': 8, 'file': "{}/sdo.img".format(image_path)})
        drives2.append({'size': 16, 'file': "{}/sdp.img".format(image_path)})
        drives2.append({'size': 8, 'file': "{}/sdq.img".format(image_path)})
        drives2.append({'size': 16, 'file': "{}/sdr.img".format(image_path)})
        self.conf['compute']['storage_backend'][2]['drives'].extend(drives2)

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)

        os.system("infrasim config add {} {}".format(self.conf["name"], tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type_ahci = run_command("infrasim node info {} | grep -c ahci".
                                           format(self.conf["name"]))
        controller_type_megasas = run_command("infrasim node info {} | grep -c megasas".
                                              format(self.conf["name"]))
        controller_type_lsi = run_command("infrasim node info {} | grep -c lsi".
                                          format(self.conf["name"]))

        self.assertEqual(int(controller_type_ahci[1]), 1)
        self.assertEqual(int(controller_type_megasas[1]), 1)
        self.assertEqual(int(controller_type_lsi[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        os.system("ls {}/{}".format(config.infrasim_home, self.conf["name"]))

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline
        storage_list = get_storage_list()
        assert len(storage_list) == 3
        for c_map in storage_list:
            if c_map.get('name') == 'ahci':
                assert len(c_map.get('buses')) == 1 * 6  # 1 controllers * 6 ports per controller
                assert len(c_map.get('disks')) == 6
            elif c_map.get('name') == 'megaraid_sas' or c_map.get('name') == 'sym53c8xx':
                assert len(c_map.get('buses')) == 1
                assert len(c_map.get('disks')) == 6
            else:
                assert False


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_four_storage_controllers(unittest.TestCase):

    @classmethod
    def setUp(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None
        for i in range(97, 120):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_four_controllers_each_with_six_drives(self):
        image_path = "{}/{}".format(config.infrasim_home, self.conf["name"])
        # Add several storage controllers/drives in node config file.
        drives = []
        drives.append({'size': 16, 'file': "{}/sdb.img".format(image_path)})
        drives.append({'size': 8, 'file': "{}/sdc.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sdd.img".format(image_path)})
        drives.append({'size': 8, 'file': "{}/sde.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sdf.img".format(image_path)})
        self.conf['compute']['storage_backend'][0]['drives'].extend(drives)
        self.conf['compute']['storage_backend'][0]['drives'][0]['file'] = fixtures.image

        controllers = []
        controllers.append({
            'type': 'megasas',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        controllers.append({
            'type': 'lsi',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        controllers.append({
            'type': 'ahci',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        self.conf['compute']['storage_backend'].extend(controllers)

        drives1 = []
        drives1.append({'size': 8, 'file': "{}/sdg.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdh.img".format(image_path)})
        drives1.append({'size': 8, 'file': "{}/sdi.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdj.img".format(image_path)})
        drives1.append({'size': 8, 'file': "{}/sdk.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdl.img".format(image_path)})
        self.conf['compute']['storage_backend'][1]['drives'].extend(drives1)

        drives2 = []
        drives2.append({'size': 8, 'file': "{}/sdm.img".format(image_path)})
        drives2.append({'size': 16, 'file': "{}/sdn.img".format(image_path)})
        drives2.append({'size': 8, 'file': "{}/sdo.img".format(image_path)})
        drives2.append({'size': 16, 'file': "{}/sdp.img".format(image_path)})
        drives2.append({'size': 8, 'file': "{}/sdq.img".format(image_path)})
        drives2.append({'size': 16, 'file': "{}/sdr.img".format(image_path)})
        self.conf['compute']['storage_backend'][2]['drives'].extend(drives2)

        drives3 = []
        drives3.append({'size': 8, 'file': "{}/sds.img".format(image_path)})
        drives3.append({'size': 16, 'file': "{}/sdt.img".format(image_path)})
        drives3.append({'size': 8, 'file': "{}/sdu.img".format(image_path)})
        drives3.append({'size': 16, 'file': "{}/sdv.img".format(image_path)})
        drives3.append({'size': 8, 'file': "{}/sdw.img".format(image_path)})
        drives3.append({'size': 16, 'file': "{}/sdx.img".format(image_path)})
        self.conf['compute']['storage_backend'][3]['drives'].extend(drives3)

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)

        os.system("infrasim config add {} {}".format(self.conf["name"], tmp_conf_file))
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        helper.port_forward(node)

        controller_type_ahci = run_command("infrasim node info {} | grep -c ahci".
                                           format(self.conf["name"]))
        controller_type_megasas = run_command("infrasim node info {} | grep -c megasas".
                                              format(self.conf["name"]))
        controller_type_lsi = run_command("infrasim node info {} | grep -c lsi".
                                          format(self.conf["name"]))

        self.assertEqual(int(controller_type_ahci[1]), 2)
        self.assertEqual(int(controller_type_megasas[1]), 1)
        self.assertEqual(int(controller_type_lsi[1]), 1)

        qemu_pid = get_qemu_pid(node)
        qemu_cmdline = open("/proc/{}/cmdline".format(qemu_pid)).read().replace("\x00", " ")

        assert "qemu-system-x86_64" in qemu_cmdline
        assert "format=qcow2" in qemu_cmdline

        storage_list = get_storage_list()

        # Only has three types of controller
        assert len(storage_list) == 3
        for c_map in storage_list:
            if c_map.get('name') == 'ahci':
                assert len(c_map.get('buses')) == 2 * 6  # 2 controllers * 6 ports per controller
                assert len(c_map.get('disks')) == 12
            elif c_map.get('name') == 'megaraid_sas' or c_map.get('name') == 'sym53c8xx':
                assert len(c_map.get('buses')) == 1
                assert len(c_map.get('disks')) == 6
            else:
                assert False


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_qemu_boot_from_disk_img_at_1st_controller(unittest.TestCase):

    @classmethod
    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        for i in range(97, 102):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_qemu_boot_from_disk_img(self):

        image_path = "{}/{}".format(config.infrasim_home, self.conf["name"])

        controllers = []
        controllers.append({
            'type': 'megasas',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        controllers.append({
            'type': 'lsi',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        self.conf['compute']['storage_backend'].extend(controllers)

        drives = []
        drives.append({'size': 8, 'file': "{}/sdc.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sdd.img".format(image_path)})
        self.conf['compute']['storage_backend'][1]['drives'].extend(drives)

        drives1 = []
        drives.append({'size': 8, 'file': "{}/sde.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sdf.img".format(image_path)})
        self.conf['compute']['storage_backend'][2]['drives'].extend(drives1)

        self.conf["compute"]["storage_backend"][0] = {
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": [{"size": 8, "bootindex": 1, "file": fixtures.image},
                       {"size": 16, "file": "{}/sdb.img".format(image_path)}]}
        print self.conf

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        set_port_forward_try_ssh(node)


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_qemu_boot_from_disk_img_at_2nd_controller(unittest.TestCase):

    @classmethod
    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        for i in range(97, 102):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_qemu_boot_from_disk_img(self):
        #
        image_path = "{}/{}".format(config.infrasim_home, self.conf["name"])
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": [{"size": 8, "file": "{}/sdb.img".format(image_path)},
                       {"size": 16, "file": "{}/sdc.img".format(image_path)}]}]

        controllers = []
        controllers.append({
            'type': 'ahci',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        controllers.append({
            'type': 'lsi',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        self.conf['compute']['storage_backend'].extend(controllers)

        drives = []
        drives.append({'size': 8, 'bootindex': 1, 'file': fixtures.image})
        drives.append({'size': 16, 'file': "{}/sdd.img".format(image_path)})
        self.conf['compute']['storage_backend'][1]['drives'].extend(drives)

        drives1 = []
        drives1.append({'size': 8, 'file': "{}/sde.img".format(image_path)})
        drives1.append({'size': 16, 'file': "{}/sdf.img".format(image_path)})
        self.conf['compute']['storage_backend'][2]['drives'].extend(drives1)
        print self.conf

        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)

        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        set_port_forward_try_ssh(node)


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_qemu_boot_from_disk_img_at_3rd_controller(unittest.TestCase):

    @classmethod
    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()

    @classmethod
    def tearDown(self):
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.conf = None
        os.system("rm /tmp/cirros-0.3.4-x86_64-disk.img")
        for i in range(97, 102):
            disk_file = "/tmp/sd{}.img".format(chr(i))
            if os.path.exists(disk_file):
                os.unlink(disk_file)

    def test_qemu_boot_from_disk_img(self):
        image_path = "{}/{}".format(config.infrasim_home, self.conf["name"])
        self.conf["compute"]["storage_backend"] = [{
            "type": "ahci",
            "use_msi": "true",
            "max_cmds": 1024,
            "max_sge": 128,
            "max_drive_per_controller": 6,
            "drives": [{"size": 8, "file": "{}/sdb.img".format(image_path)},
                       {"size": 16, "file": "{}/sdc.img".format(image_path)}]}]
        controllers = []
        controllers.append({
            'type': 'ahci',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
        })
        controllers.append({
            'type': 'lsi',
            'use_msi': 'true',
            'max_cmds': 1024,
            'max_sge': 128,
            'drives': [],
            'max_drive_per_controller': 6
            })
        self.conf['compute']['storage_backend'].extend(controllers)
        drives = []
        drives.append({'size': 8, 'file': "{}/sdd.img".format(image_path)})
        drives.append({'size': 16, 'file': "{}/sde.img".format(image_path)})
        self.conf['compute']['storage_backend'][1]['drives'].extend(drives)
        drives1 = []
        drives1.append({'size': 8, 'file': "{}/sdf.img".format(image_path)})
        drives1.append({'size': 16, 'bootindex': 1, 'file': fixtures.image})
        self.conf['compute']['storage_backend'][2]['drives'].extend(drives1)
        print self.conf
        with open('/tmp/test.yml', 'w') as outfile:
            yaml.dump(self.conf, outfile, default_flow_style=False)
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        set_port_forward_try_ssh(node)
