"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
import unittest
import os
import json
import time
from infrasim import model
from infrasim import helper
from infrasim.helper import UnixSocket
from infrasim import sshclient
from test import fixtures


old_path = os.environ.get('PATH')
new_path = '{}/bin:{}'.format(os.environ.get('PYTHONPATH'), old_path)
conf = {}


def setup_module():
    os.environ['PATH'] = new_path


def teardown_module():
    os.environ['PATH'] = old_path


class test_drive_insert(unittest.TestCase):

    @staticmethod
    def start_node():
        global conf
        global path
        nvme_config = fixtures.NvmeConfig()
        conf = nvme_config.get_node_info()
        conf["compute"]["boot"] = {
            "boot_order": "c"
        }
        conf["compute"]["storage_backend"] = [
            {
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [
                    {
                        "size": 40,
                        "model": "SATADOM",
                        "serial": "20160518AA851134100",
                        "file": fixtures.image
                    }
                ]
            },
            {
                "cmb_size_mb": 1,
                "drives": [
                    {
                        "size": 8
                    }
                ],
                "lba_index": 0,
                "namespaces": 2,
                "serial": "0400001C1FFA",
                "bus": "downstream2",
                "type": "nvme",
                "oncs": "0xf"

            },
            {
                "cmb_size_mb": 1,
                "drives": [
                    {
                        "size": 8
                    }
                ],
                "lba_index": 0,
                "namespaces": 3,
                "bus": "downstream3",
                "serial": "0400001C6BB4",
                "type": "nvme",
                "oncs": "0xf"
            }]
        conf["compute"]["networks"] = [{
            "bus": "downstream1",
            "device": "e1000",
            "mac": "52:54:be:b9:77:dd",
            "network_mode": "nat",
            "network_name": "dummy0"
        }]
        conf["compute"]["pcie_topology"] = {
            "root_port": [
                {
                    "addr": "7.0",
                    "bus": "pcie.0",
                    "chassis": 1,
                    "device": "ioh3420",
                    "id": "root_port1",
                    "pri_bus": 0,
                    "sec_bus": 40,
                    "slot": 2
                },
                {
                    "addr": "8.0",
                    "bus": "pcie.0",
                    "chassis": 1,
                    "device": "ioh3420",
                    "id": "root_port2",
                    "pri_bus": 0,
                    "sec_bus": 60,
                    "slot": 3
                }
            ],
            "switch": [
                {
                    "downstream": [
                        {
                            "addr": "2.0",
                            "bus": "upstream1",
                            "chassis": 1,
                            "device": "xio3130-downstream",
                            "id": "downstream1",
                            "slot": 190,
                            "pri_bus": 41,
                            "sec_bus": 42
                        },
                        {
                            "addr": "3.0",
                            "bus": "upstream1",
                            "chassis": 1,
                            "device": "xio3130-downstream",
                            "id": "downstream2",
                            "slot": 160,
                            "pri_bus": 41,
                            "sec_bus": 43
                        }
                    ],
                    "upstream": [
                        {
                            "bus": "root_port1",
                            "device": "x3130-upstream",
                            "id": "upstream1"
                        }
                    ]
                },
                {
                    "downstream": [
                        {
                            "addr": "2.0",
                            "bus": "upstream2",
                            "chassis": 1,
                            "device": "xio3130-downstream",
                            "id": "downstream3",
                            "slot": 193,
                            "pri_bus": 61,
                            "sec_bus": 62
                        },
                        {
                            "addr": "3.0",
                            "bus": "upstream2",
                            "chassis": 1,
                            "device": "xio3130-downstream",
                            "id": "downstream4",
                            "slot": 164,
                            "pri_bus": 61,
                            "sec_bus": 63
                        }
                    ],
                    "upstream": [
                        {
                            "bus": "root_port2",
                            "device": "x3130-upstream",
                            "id": "upstream2"
                        }
                    ]
                }
            ]
        }
        node = model.CNode(conf)
        node.init()
        node.precheck()
        node.start()
        node.wait_node_up(3)
        helper.port_forward(node)
        node.wait_node_up(3)
        path = os.path.join(node.workspace.get_workspace(), ".monitor")

    @staticmethod
    def stop_node():
        global conf
        node = model.CNode(conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        conf = {}

    @classmethod
    def setUpClass(cls):
        cls.start_node()

    @classmethod
    def tearDownClass(cls):
        if conf:
            cls.stop_node()

    def test_step1_nvmedrive_remove(self):
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        ssh.connect()
        s = UnixSocket(path)
        s.connect()
        s.recv()

        # 1.1: remove drive
        status, stdout = ssh.exec_command('nvme list')
        self.assertIn('0400001C6BB4', stdout, "Failed: didn't find dev-nvme-1")

        payload_enable_qmp = {
            "execute": "qmp_capabilities"
        }
        s.send(json.dumps(payload_enable_qmp))
        s.recv()

        payload_drive_remove = {
                "execute": "human-monitor-command",
                "arguments": {
                 "command-line": "device_del dev-nvme-1"
                }
        }
        s.send(json.dumps(payload_drive_remove))
        s.close()
        # around 10s is necessary for refresh the device list
        time.sleep(10)
        status, stdout = ssh.exec_command('nvme list')
        self.assertNotIn('0400001C6BB4', stdout, "NVME drive remove failed")

    def test_step2_nvmedrive_insert(self):
        ssh = sshclient.SSH("127.0.0.1", "root", "root", port=2222)
        ssh.connect()
        s = UnixSocket(path)
        s.connect()
        s.recv()
        status, stdout = ssh.exec_command('nvme list')
        self.assertNotIn('SSD00000001', stdout, "Failed: SN is duplicate")

        # 2.1: insert known NVME drive
        payload_enable_qmp = {
            "execute": "qmp_capabilities"
        }
        s.send(json.dumps(payload_enable_qmp))
        s.recv()

        payload_drive_insert = {
                "execute": "human-monitor-command",
                "arguments": {
                    "command-line": "device_add nvme,"
                                    "id=dev-nvme-1,drive=nvme-1,"
                                    "model_number=INTEL-SSD00000001,"
                                    "serial=FUKD72220009375A01,"
                                    "bus=downstream4,cmb_size_mb=1"
                }
        }
        s.send(json.dumps(payload_drive_insert))
        time.sleep(5)
        status, stdout = ssh.exec_command('nvme list')
        self.assertIn('SSD00000001', stdout, "NVME drive insert failed")

        # 2.2: IO test, nvme1n1, SSD00000001
        status, stdout = ssh.exec_command(
            'sudo fio -filename=/dev/nvme1n1  -direct=1 -iodepth 1 -thread \
             -rw=write -ioengine=psync -bs=4k -size=10M -numjobs=10 \
             -runtime=100 -do_verify=1 -group_reporting -name=mytest')
        self.assertNotIn('error', stdout, "New NVME drive r/w test failed")
        s.close()
