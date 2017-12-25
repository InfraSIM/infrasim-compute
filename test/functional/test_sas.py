'''
*********************************************************
Copyright @ 2017 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import time
import yaml
import shutil
from infrasim import model
from infrasim import helper
from infrasim import InfraSimError
import paramiko
from test import fixtures


"""
Test inquiry/mode sense data injection of scsi drive
"""
file_prefix = os.path.dirname(os.path.realpath(__file__))
test_img_file = "/tmp/kcs.img"
test_drive_image = "/tmp/test_drv{}.img"
conf = {}
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None
wwn_drv = 5764824129059301745
wwn_exp0 = 5764611469514216599
wwn_exp1 = 5764611469514216699


def setup_module():
    test_img_file = "/tmp/kcs.img"
    DOWNLOAD_URL = "https://github.com/InfraSIM/test/raw/master/image/kcs.img"
    MD5_KCS_IMG = "986e5e63e8231a307babfbe9c81ca210"
    try:
        helper.fetch_image(DOWNLOAD_URL, MD5_KCS_IMG, test_img_file)
    except InfraSimError as e:
        print e.value
        assert False

    os.environ["PATH"] = new_path
    if os.path.exists("/tmp/topo"):
        shutil.rmtree("/tmp/topo")
    os.makedirs("/tmp/topo")


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
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["boot"] = {
        "boot_order": "c"
        }

    conf["compute"]["storage_backend"] = [
        {
            "type": "ahci",
            "max_drive_per_controller": 6,
            "drives": [
                {
                    "size": 8,
                    "file": test_img_file
                }
            ]
        },
        {
            "type": "lsisas3008",
            "max_drive_per_controller": 32,
            "connectors": [
                {
                    "phy": 0,
                    "wwn": 5764824129059291136,
                    "atta_enclosure": "enclosure_0",
                    "atta_exp": "lcc-a",
                    "atta_port": 0
                },
                {
                    "phy": 4,
                    "wwn": 5764824129059291137,
                    "atta_enclosure": "enclosure_0",
                    "atta_exp": "lcc-b",
                    "atta_port": 0
                }
            ]
        },
        {
            "type": "disk_array",
            "disk_array": [
                {
                    "enclosure": {
                        "type": 28,
                        "drives": [
                            {
                                "repeat": 8,
                                "start_phy_id": 12,
                                "format": "raw",
                                "share-rw": "true",
                                "version": "B29C",
                                "file": "/tmp/topo/sda{}.img",
                                "slot_number": 0,
                                "serial": "ZABCD{}",
                                "wwn": wwn_drv
                            }
                        ],
                        "expanders": [
                            {
                                "phy_count": 36,
                                "wwn": wwn_exp0,
                                "ports": [
                                    {
                                        "phy": 0,
                                        "id": 0,
                                        "number": 4
                                    },
                                    {
                                        "phy": 4,
                                        "id": 1,
                                        "number": 4
                                    }
                                ],
                                "side": 0,
                                "name": "lcc-a"
                            },
                            {
                                "phy_count": 36,
                                "wwn": wwn_exp1,
                                "ports": [
                                    {
                                        "phy": 0,
                                        "id": 0,
                                        "number": 4
                                    },
                                    {
                                        "phy": 4,
                                        "id": 1,
                                        "number": 4
                                    }
                                ],
                                "side": 1,
                                "name": "lcc-b"
                            }
                        ]
                    },
                    "name": "enclosure_0"
                }
            ]
        }
    ]

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()

    helper.port_forward(node)
    ssh = helper.prepare_ssh()


def stop_node():
    global conf
    global tmp_conf_file
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}
    shutil.rmtree("/tmp/topo", True)


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


class test_disk_array_topo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node(node_type="quanta_d51")

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_sasi_disk_serial(self):
        # check the availability of drives and enclosures.
        drv_list = run_cmd("ls /dev/sd*").split(" ")
        for i in drv_list:
            rst = run_cmd("sg_inq {0}".format(i))
            if "B29C" in rst:
                self.assertIn("ZABCD0", rst, "Serial Number not as expected:\n"
                              "{}".format(rst))

    def test_scsi_devices_availability(self):
        rst = run_cmd("lspci")
        self.assertIn("Serial Attached SCSI controller: LSI Logic", rst,
                      "SAS Controller not loaded!")

        # check the wwn and type of devices
        rst = run_cmd("for f in /sys/bus/scsi/devices/0*;"
                      "do cat $f/type | tr '\n' ' ' && cat $f/sas_address; done")
        rst_lines = rst.splitlines()
        # prepare expected string. 0 end device, 13 enclosure.
        # 8 drives(2 ports for each) and 2 enclosure.
        expect = {}
        for i in range(8):
            expect["0 "+hex(wwn_drv + i * 4 + 1)] = False
            expect["0 "+hex(wwn_drv + i * 4 + 2)] = False
        expect["13 "+hex(wwn_exp0 - 1)] = False
        expect["13 "+hex(wwn_exp1 - 1)] = False
        # check the returned content.
        for line in rst_lines:
            expect.update({line: True})
        for key, val in expect.iteritems():
            self.assertTrue(
                val, "SCSI Device not found in sys: {0}".format(key))
