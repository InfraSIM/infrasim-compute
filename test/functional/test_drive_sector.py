'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
from infrasim import model
from infrasim import helper
import paramiko
from test import fixtures
import re


conf = None
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


def start_node():
    """
    create two drive for comparasion.
    First drive has additional page, second doesn't
    """
    global conf
    global tmp_conf_file
    global ssh

    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["networks"][0]["port_forward"] = [
        {
            "protocal": "tcp",
            "inside": 22,
            "outside": 2222
        }
    ]

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
            "type": "lsi",
            "max_drive_per_controller": 16,
            "drives": [
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
                    "scsi-id": 0,
                    "slot_number": 0,
                    "sector_size": 520
                },
                {
                    "format": "raw",
                    "size": 1,
                    "vendor": "HITACH",
                    "product": "ST4000NM0006",
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

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()

    # wait until system is ready for ssh.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    helper.try_func(600, paramiko.SSHClient.connect, ssh, "127.0.0.1",
                    port=2222, username="root", password="root", timeout=120)


def stop_node():
    global conf
    global ssh
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = None
    ssh.close()


def run_cmd(cmd):
    global ssh
    _, stdout, _ = ssh.exec_command(cmd)
    while not stdout.channel.exit_status_ready():
        pass
    lines = stdout.channel.recv(4096)
    return lines


class test_drive_sector_size(unittest.TestCase):

    drv_520 = None
    drv_512 = None

    @classmethod
    def setUpClass(cls):
        start_node()

        def find_dev_name(index, lines):
            vender = conf["compute"]["storage_backend"][1]["drives"][index]["vendor"]
            s = re.search(r'(/dev/sg.+)\s+/dev/sd.+\s+{}\s+'.format(vender), lines)
            return s.group(1) if s else None

        # get dev name like /dev/sg*
        lines = run_cmd("sg_map -n -i")
        cls.drv_520 = find_dev_name(0, lines)
        cls.drv_512 = find_dev_name(1, lines)
        assert cls.drv_520
        assert cls.drv_512

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_sas_sector_520(self):
        lines = run_cmd("sg_readcap {0}".format(test_drive_sector_size.drv_520))
        self.assertIn("Logical block length=520 bytes", lines,
                      "incorrect Logical block length of {0}".format(test_drive_sector_size.drv_520))

    def test_sas_sector_520_read_write(self):
        # prepare data.
        data = "\\xff\\x01\\x02\\x03\\x04\\x05\\x06\\x07"
        for _ in range(0, 504 / 8):
            data = data + "\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"
        data = data + "\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\xff"
        # write 520 bytes to 2rd sector.
        cmd = "echo -ne '{0}' | sg_dd of={1} bs=520 seek=1".format(data, test_drive_sector_size.drv_520)
        run_cmd(cmd)
        # read sectors and verify.
        cmd = "sg_dd if={0} bs=520 count=3 | hd".format(test_drive_sector_size.drv_520)
        lines = run_cmd(cmd)

        self.assertIn("00000200  00 00 00 00 00 00 00 00  ff 01 02 03 04 05 06 07", lines, "sector start error")
        self.assertIn("00000400  00 00 00 00 00 00 00 00  01 02 03 04 05 06 07 ff", lines, "sector end error")

    def test_sas_sector_512(self):
        lines = run_cmd("sg_readcap {0}".format(test_drive_sector_size.drv_512))
        self.assertIn("Logical block length=512 bytes", lines,
                      "incorrect Logical block length of {0}".format(test_drive_sector_size.drv_512))
