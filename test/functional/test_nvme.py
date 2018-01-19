"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import yaml
import time
import paramiko
import subprocess
import re
import json
from infrasim import model
from infrasim import helper
from infrasim.helper import UnixSocket
from test import fixtures

old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)


def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path


class test_nvme(unittest.TestCase):
    global tmp_conf_file
    global format_f
    global test_img_file
    global conf
    conf = {}

    @staticmethod
    def start_node():
        global conf
        global sas_drive_serial
        global sata_drive_serial
        global boot_drive_serial
        nvme_config = fixtures.NvmeConfig()
        conf = nvme_config.get_node_info()
        node = model.CNode(conf)
        node.init()
        node.precheck()
        node.start()
        time.sleep(3)
        helper.port_forward(node)

    @staticmethod
    def stop_node():
        global conf
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        conf = {}

        time.sleep(5)

    @classmethod
    def setUpClass(cls):
        cls.start_node()

    @classmethod
    def tearDownClass(cls):
        if conf:
            cls.stop_node()

    def get_nvme_disks(self):
        ssh = helper.prepare_ssh()
        nvme_list = []
        stdin, stdout, stderr = ssh.exec_command("sudo nvme list |grep \"/dev\" |awk '{print $1}'")
        while not stdout.channel.exit_status_ready():
            pass
        nvme_list = stdout.channel.recv(2048).split()
        ssh.close()
        return nvme_list

    def test_nvme_disk_count(self):
        global conf
        nvme_list = self.get_nvme_disks()
        nvme_config_list = []
        for drive in conf["compute"]["storage_backend"]:
            if drive["type"] == "nvme":
                nvme_config_list.append(drive)
        assert len(nvme_list) == len(nvme_config_list)

    def test_read_write_verify(self):
        nvme_list = self.get_nvme_disks()
        ssh = helper.prepare_ssh()
        for dev in nvme_list:
            # Write 0xff to 2048 byte of nvme disks
            stdin, stdout, stderr = ssh.exec_command("nvme write {} -d ff_binfile -z 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            # Verify data consistent as written
            stdin, stdout, stderr = ssh.exec_command("nvme read {} -z 2048 >read_data".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("hexdump read_data -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            read_data = stdout.channel.recv(2048)

            stdin, stdout, stderr = ssh.exec_command("hexdump ff_binfile".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            binfile_data = stdout.channel.recv(2048)
            assert read_data == binfile_data

            # restore drive data to all zero
            stdin, stdout, stderr = ssh.exec_command("nvme write {} -d 0_binfile -z 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("nvme read {} -z 2048 >read_data".format(dev))
            while not stdout.channel.exit_status_ready():
                pass

            stdin, stdout, stderr = ssh.exec_command("hexdump read_data -n 2048".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            read_data = stdout.channel.recv(2048)

            stdin, stdout, stderr = ssh.exec_command("hexdump 0_binfile".format(dev))
            while not stdout.channel.exit_status_ready():
                pass
            binfile_data = stdout.channel.recv(2048)
            assert read_data == binfile_data
        ssh.close()
