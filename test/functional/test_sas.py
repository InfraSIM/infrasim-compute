'''
*********************************************************
Copyright @ 2017 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import shutil
import re
from infrasim import model
from infrasim import helper
import paramiko
from test import fixtures

"""
Test inquiry/mode sense data injection of scsi drive
"""
file_prefix = os.path.dirname(os.path.realpath(__file__))
test_drive_array_image = "/tmp/test_drv{}.img"
test_drive_directly_image = "/tmp/empty_scsi.img"
conf = {}
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
ssh = None
wwn_drv = 5764824129059301745
drv_count = 8
wwn_drv1 = 5764824129059311745
drv1_count = 4
wwn_exp0 = 5764611469514216599
wwn_exp1 = 5764611469514216699

wwn_exp2 = 5764611469514216799
wwn_exp3 = 5764611469514216899


def setup_module():
    os.environ["PATH"] = new_path
    if os.path.exists("/tmp/topo"):
        shutil.rmtree("/tmp/topo")
    os.makedirs("/tmp/topo")


def teardown_module():
    global conf
    if conf:
        stop_node()
    os.environ["PATH"] = old_path
    shutil.rmtree("/tmp/topo", True)


def start_node_enclosure():
    global ssh
    global conf
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
                    "file": fixtures.image
                }
            ]
        },
        {
            "type": "lsisas3008",
            "sas_address": 5764824129059291136,
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
                                "repeat": drv_count,
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
                                "phy_map": "35-10,8,9",
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
                                "name": "lcc-a",
                                "ses": {
                                    "buffer_data": "/home/infrasim/workspace/bins/buffer.bin"
                                }
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
                                "name": "lcc-b",
                                "ses": {
                                    "buffer_data": "/home/infrasim/workspace/bins/buffer.bin"
                                }
                            }
                        ]
                    },
                    "name": "enclosure_0"
                },
                {
                    "enclosure": {
                        "type": 28,
                        "drives": [
                            {
                                "repeat": drv1_count,
                                "start_phy_id": 12,
                                "format": "raw",
                                "share-rw": "true",
                                "version": "B29C",
                                "file": "/tmp/topo/sdb{}.img",
                                "slot_number": 0,
                                "serial": "ZABCE{}",
                                "wwn": wwn_drv1
                            }
                        ],
                        "expanders": [
                            {
                                "phy_count": 36,
                                "wwn": wwn_exp2,
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
                                "name": "lcc-a",
                                "ses": {
                                    "buffer_data": "/home/infrasim/workspace/bins/buffer.bin"
                                }
                            },
                            {
                                "phy_count": 36,
                                "wwn": wwn_exp3,
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
                                "name": "lcc-b",
                                "ses": {
                                    "buffer_data": "/home/infrasim/workspace/bins/buffer.bin"
                                }
                            }
                        ]
                    },
                    "name": "enclosure_1"
                },
                {
                    "connections": [
                        {"link": [
                            {
                                "disk_array": "enclosure_0",
                                "exp": "lcc-a",
                                "number": 4,
                                "phy": 4
                            },
                            {
                                "disk_array": "enclosure_1",
                                "exp": "lcc-a",
                                "number": 4,
                                "phy": 0
                            }
                        ]},
                        {"link": [
                            {
                                "disk_array": "enclosure_0",
                                "exp": "lcc-b",
                                "number": 4,
                                "phy": 4
                            },
                            {
                                "disk_array": "enclosure_1",
                                "exp": "lcc-b",
                                "number": 4,
                                "phy": 0
                            }
                        ]
                        }
                    ]
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


def start_node_directly():
    global conf
    global tmp_conf_file
    global ssh
    os.system("touch {0}".format(test_drive_directly_image))
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
                    "file": fixtures.image
                }
            ]
        },
        {
            "type": "lsisas3008",
            "max_drive_per_controller": 32,
            "drives": [
                {
                    "file": test_drive_directly_image,
                    "format": "raw",
                    "vendor": "SEAGATE",
                    "product": "ST4000NM0005",
                    "serial": "01234567",
                    "version": "M001",
                    "wwn": "0x5000C500852E2971",
                    "share-rw": "true",
                    "cache": "none",
                    "scsi-id": 0,
                    "slot_number": 0
                },
                {
                    "file": test_drive_directly_image,
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

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()

    helper.port_forward(node)
    ssh = helper.prepare_ssh()


def stop_node():
    global conf
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = None


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
        start_node_enclosure()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_sas_disk_serial(self):
        # check the availability of drives and enclosures.
        drv_list = run_cmd("ls /dev/sd*").split("\n")
        for i in drv_list:
            rst = run_cmd("sg_inq {0}".format(i))
            if "B29C" in rst:
                self.assertIn("Unit serial number: ZABC", rst, "Serial Number not as expected:\n"
                              "{}".format(rst))

    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests, Known issue: IN-1619")
    def test_scsi_devices_availability(self):
        """
        Verify all devices can be found by OS.
        """
        rst = run_cmd("lspci")
        self.assertIn("Serial Attached SCSI controller: LSI Logic", rst, "SAS Controller not loaded!")

        # check the wwn and type of devices
        rst = run_cmd("for f in /sys/bus/scsi/devices/6*;"
                      "do cat $f/type | tr '\n' ' ' && cat $f/sas_address; done")
        rst_lines = rst.splitlines()
        # prepare expected string. type=0:end device, type=13:enclosure.
        # drives with 2 ports for each and seses.
        expect = {}
        for i in range(drv_count):
            expect["0 " + hex(wwn_drv + i * 4 + 1)] = 0
            expect["0 " + hex(wwn_drv + i * 4 + 2)] = 0

        expect["13 " + hex(wwn_exp0 - 1)] = 0
        expect["13 " + hex(wwn_exp1 - 1)] = 0

        for i in range(drv1_count):
            expect["0 " + hex(wwn_drv1 + i * 4 + 1)] = 0
            expect["0 " + hex(wwn_drv1 + i * 4 + 2)] = 0

        expect["13 " + hex(wwn_exp2 - 1)] = 0
        expect["13 " + hex(wwn_exp3 - 1)] = 0
        # check the returned content.
        if rst_lines:
            for line in rst_lines:
                expect[line] = expect.get(line) + 1
            for key, val in expect.iteritems():
                self.assertEqual(val, 1, "SCSI Device count error in sys: {0} count={1}".format(key, val))

    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests, Known issue: IN-1619")
    def test_sas_chain(self):
        """
        Verify the connection between expanders
        """
        topology = {}

        def split_link(msg):
            """
            a helper to extract connection to another expander
            """
            msg = msg.rstrip().split('\n')
            result = {}
            for link in msg:
                m = re.match(
                    "^\s+phy\s+(?P<phy>\d+):.:attached:\[(?P<atta_wwn>[0-9a-f]+):(?P<atta_phy>\d+) exp .*\]", link)
                if m:
                    item = {"atta_wwn": "0x" + m.group("atta_wwn"), "atta_phy": int(m.group("atta_phy"))}
                    result[int(m.group("phy"))] = item
            # "  phy   0:U:attached:[50000396dc89949f:04 exp i(SSP+STP+SMP)]  12 Gbps"
            return result

        def verify_link(wwn, phy, atta_wwn, atta_phy, number):
            """
            helper to verify connection in both direction.
            """
            def verify(wwn, phy, atta_wwn, atta_phy):
                """
                verify connection in one direction.
                """
                self.assertIn(wwn, topology.keys(), "Mismatch expander [{}]".format(wwn))
                links = topology[wwn]["subs"]
                self.assertIn(phy, links.keys(), "Mismatch phy {} in expander {}".format(phy, wwn))
                atta = links[phy]
                self.assertEqual(
                    atta_wwn, atta["atta_wwn"],
                    "Mismatch atta_wwn {} in phy {} of exp {}".format(atta_wwn, phy, wwn))
                self.assertEqual(
                    atta_phy, atta["atta_phy"],
                    "Mismatch atta_phy {} in phy {} of exp {}".format(atta_phy, phy, wwn))

            # verify conections
            wwn = hex(wwn)
            atta_wwn = hex(atta_wwn)
            for index in range(number):
                verify(wwn, phy + index, atta_wwn, atta_phy + index)
                verify(atta_wwn, atta_phy + index, wwn, phy + index)

        # prepare the list of expander's wwn
        content = run_cmd("ls -1 /dev/bsg/expander-*")
        exp_list = content.rstrip().split('\n')
        for name in exp_list:
            content = run_cmd("sudo smp_discover {}".format(name))
            exp_child = split_link(content)

            content = run_cmd("sudo smp_discover -M {}".format(name))
            exp_wwn = content.rstrip()

            topology[exp_wwn] = {"name": name, "subs": exp_child}

        # verify connection between expanders.
        verify_link(wwn_exp0, 4, wwn_exp2, 0, 4)
        verify_link(wwn_exp1, 4, wwn_exp3, 0, 4)


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests, Known issue: IN-1619")
class test_disk_directly(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests, Known issue: IN-1619")
    def setUpClass(cls):
        start_node_directly()

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests, Known issue: IN-1619")
    def tearDownClass(cls):
        stop_node()

    def test_sas_directly(self):
        lines = run_cmd("lsscsi -w")
        print("\n")
        print(lines)
        reobj = re.search("0x5000C500852E3141", lines, re.IGNORECASE)
        assert reobj
        reobj = re.search("0x5000C500852E2971", lines, re.IGNORECASE)
        assert reobj
