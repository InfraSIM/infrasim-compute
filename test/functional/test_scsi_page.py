'''
*********************************************************
Copyright @ 2017 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import time
import yaml
import json
from infrasim import model
from infrasim import helper
from infrasim.helper import UnixSocket
import paramiko
from test import fixtures
import re


"""
Test inquiry/mode sense data injection of scsi drive
"""
file_prefix = os.path.dirname(os.path.realpath(__file__))
test_drive_image = "/tmp/empty_scsi.img"
page_file = file_prefix + "/fake_page.bin"
conf = {}
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    global conf
    if conf:
        stop_node()
    os.environ["PATH"] = old_path


def start_node(node_type):
    """
    create two drive for comparasion.
    First drive has additional page, second doesn't
    """
    global conf
    global tmp_conf_file
    global ssh
    # create a empty image for test.
    os.system("touch {0}".format(test_drive_image))
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["type"] = node_type

    conf["compute"]["storage_backend"] = [
        {
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [
                {
                    "size": 8,
                    "file": fixtures.image
                }
            ]
        },
        {
            "type": "megasas",
            "max_drive_per_controller": 16,
            "drives": [
                {
                    "file": test_drive_image,
                    "format": "raw",
                    "vendor": "SEAGATE",
                    "product": "ST4000NM0005",
                    "serial": "01234567",
                    "version": "M001",
                    "wwn": "0x5000C500852E2971",
                    "share-rw": "true",
                    "cache": "none",
                    "scsi-id": 0,
                    "slot_number": 0,
                    "page-file": page_file
                },
                {
                    "file": test_drive_image,
                    "format": "raw",
                    "vendor": "SEAGATE",
                    "product": "ST4000NM0005",
                    "serial": "12345678",
                    "version": "M001",
                    "wwn": "0x5000C500852E3141",
                    "share-rw": "true",
                    "cache": "none",
                    "scsi-id": 1,
                    "slot_number": 1
                }
            ]
        }
    ]

    with open(tmp_conf_file, "w") as yaml_file:
        yaml.dump(conf, yaml_file, default_flow_style=False)

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()

    time.sleep(3)

    # Port forward from guest 22 to host 2222
    path = os.path.join(node.workspace.get_workspace(), ".monitor")
    s = UnixSocket(path)
    s.connect()
    s.recv()

    payload_enable_qmp = {
        "execute": "qmp_capabilities"
    }

    s.send(json.dumps(payload_enable_qmp))
    s.recv()

    payload_port_forward = {
        "execute": "human-monitor-command",
        "arguments": {
            "command-line": "hostfwd_add ::2222-:22"
        }
    }
    s.send(json.dumps(payload_port_forward))
    s.recv()

    s.close()

    time.sleep(3)
# wait until system is ready for ssh.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="root", password="root", timeout=120)
    ssh.close()


def stop_node():
    global conf
    global tmp_conf_file
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}
    if os.path.exists(tmp_conf_file):
        os.unlink(tmp_conf_file)

    # remove the empty image for test.
    os.remove(test_drive_image)
    time.sleep(5)


def run_cmd(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="root", password="root", timeout=120)

    stdin, stdout, stderr = ssh.exec_command(cmd)
    while not stdout.channel.exit_status_ready():
        pass
    lines = stdout.channel.recv(4096)
    ssh.close()
    return lines


class test_scsi_drive_pages(unittest.TestCase):

    drv_page = ""
    drv_nopage = ""

    @classmethod
    def setUpClass(cls):
        start_node(node_type="quanta_d51")

        # look for correct drv name according to wwn.
        def find_dev_name(index, lines):
            wwn = conf["compute"]["storage_backend"][1]["drives"][index]["wwn"].lower()
            s = re.search(r'disk\s+{}\s+(.*)'.format(wwn), lines)
            return s.group(1) if s else None

        lines = run_cmd("lsscsi -w")
        cls.drv_page = find_dev_name(0, lines)
        cls.drv_nopage = find_dev_name(1, lines)

        assert cls.drv_page
        assert cls.drv_nopage

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_inq_page_0_extra(self):
        lines = run_cmd("sg_inq {} --page=0".format(test_scsi_drive_pages.drv_page))
        print("\n")
        print(lines)
        assert "0x87" in lines
        assert "0x8a" in lines
        assert "0xc1" in lines
        assert "0xc2" in lines

    def test_inq_page_0_no_page_file(self):
        lines = run_cmd("sg_inq {} --page=0".format(test_scsi_drive_pages.drv_nopage))
        print("\n")
        print(lines)
        assert "0x87" not in lines
        assert "0x8a" not in lines
        assert "0xc1" not in lines
        assert "0xc2" not in lines

    def test_inq_page_c2(self):
        lines = run_cmd("sg_inq {} --page=0xc2 -H".format(test_scsi_drive_pages.drv_page))
        print("\n")
        print(lines)
        assert "00 c2 00 02 3c 3c" in lines

    def test_mode_pages_with_extra(self):
        lines = run_cmd("sg_modes {} -HH".format(test_scsi_drive_pages.drv_page))
        print("\n")
        print(lines)
        assert "page_code=0x2" in lines
        assert "82 0e" in lines
        assert "page_code=0x1a" in lines
        assert "9a 26" in lines
        assert "page_code=0x1" in lines
        assert "page_code=0x4" in lines
        assert "page_code=0x5" in lines
        assert "page_code=0x8" in lines

    def test_mode_pages_origin(self):
        lines = run_cmd("sg_modes {} -HH".format(test_scsi_drive_pages.drv_nopage))
        print("\n")
        print(lines)
        assert "page_code=0x2" not in lines
        assert "82 0e" not in lines
        assert "page_code=0x1a" not in lines
        assert "9a 26" not in lines
        assert "page_code=0x1" in lines
        assert "page_code=0x4" in lines
        assert "page_code=0x5" in lines
        assert "page_code=0x8" in lines
