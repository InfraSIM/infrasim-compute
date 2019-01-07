"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import re
from infrasim import model
from infrasim import helper
from test import fixtures
from infrasim.helper import UnixSocket
from infrasim import sshclient
from infrasim.config import infrasim_home

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
drive_test_image = os.path.join(infrasim_home, "test_drive_capacity.img")
conf = {}


def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path


def start_node():
    global conf
    global path
    nvme_config = fixtures.NvmeConfig()
    conf = nvme_config.get_node_info()
    conf["compute"]["boot"] = {
        "boot_order": "c"
    }
    conf["compute"]["memory"] = {
        "size": 4096
    }
    conf["compute"]["storage_backend"] = [
        {
            "type": "lsi",
            "max_drive_per_controller": 6,
            "drives": [
                {
                    "size": 10,
                    "model": "SATADOM",
                    "serial": "20160518AA851134100",
                    "file": fixtures.image
                },
                {
                    "format": "raw",
                    "size": 1,
                    "vendor": "SEAGATE",
                    "product": "ST4000NM0005",
                    "serial": "01234567",
                    "version": "M001",
                    "wwn": "0x5000C500852E2971",
                    "share-rw": "true",
                    "cache": "none",
                    "scsi-id": 1,
                    "slot_number": 0,
                    "sector_size": 520,
                    "file": drive_test_image
                 }
            ]
        }]
    conf["compute"]["networks"] = [
        {
            "bus": "pcie.0",
            "device": "e1000",
            "mac": "52:54:be:b9:77:dd",
            "network_mode": "nat",
            "network_name": "dummy0",
        }]
    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()
    node.wait_node_up(timeout=20)
    helper.port_forward(node)
    path = os.path.join(node.workspace.get_workspace(), ".monitor")


def stop_node():
    global conf
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}


class test_drive_capacity_consistency_1st(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        cmd = "sudo rm {}".format(drive_test_image)
        os.system(cmd)
        if conf:
            stop_node()

    def test_drive_capacity_consistency(self):
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        assert ssh.wait_for_host_up() is True
        s = UnixSocket(path)
        s.connect()
        s.recv()

        # 1. expect: yml img zise == host disk size
        cmd = "qemu-img info {}".format(drive_test_image)
        r = os.popen(cmd)
        img_info = r.read()
        r.close()
        self.assertIn('virtual size: 1.0G', img_info, "Existing host drive image \
                                                       size is different from the size defined in yaml")
        # 2. expect: yml img size == guest disk size
        status, stdout = ssh.exec_command('sg_readcap /dev/sdb')
        self.assertIn('Device size: 1073741760 bytes', stdout, "Guest drive image \
                                                                size is different from the size defined in yaml")
        last_lba = re.search("Last logical block address=([0-9]{0,7})", stdout).group(1)
        invalid_lba = int(last_lba) + 1
        # 3. expect: report failed when access lba range out of 1G
        status, sg_info = ssh.exec_command("sg_map -i | grep sdb")
        assert re.search("ST4000NM0005", sg_info).group()
        sg_index = re.search("sg([0-9]{1,2})", sg_info).group(1)
        cmd = "sg_dd if=/dev/sg{0} bs=520 count=1 skip={1}".format(sg_index, last_lba)
        status, stdout = ssh.exec_command(cmd)
        self.assertNotIn('failed', stdout, 'Failed, read failed when lba is valid')
        cmd = "sg_dd if=/dev/sg{0} bs=520 count=1 skip={1}".format(sg_index, str(invalid_lba))
        status, stdout = ssh.exec_command(cmd)
        self.assertIn('failed', stdout, 'Failed, read success when lba out of range')
        s.close


class test_drive_capacity_consistency_2nd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cmd = "sudo qemu-img resize -f raw {} 40G".format(drive_test_image)
        os.popen(cmd)
        start_node()

    @classmethod
    def tearDownClass(cls):
        cmd = "sudo rm {}".format(drive_test_image)
        os.system(cmd)
        if conf:
            stop_node()

    def test_drive_capacity_consistency(self):
        # 4. resize the host img to 40G, restart node, warnning is expected
        r = os.popen("cat /var/log/infrasim/nvme/runtime.log")
        rdata = r.read()
        self.assertNotIn('WARNING: Existing drive image size 40GB is different from the size 1GB defined in yaml',
                         rdata, 'Failed, Expect an image size warning to be returned')
