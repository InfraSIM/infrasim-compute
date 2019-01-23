'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import json
import math
import time
from infrasim import model
from infrasim.helper import UnixSocket
from infrasim import sshclient
from test import fixtures


conf = {}
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
inface = " "


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    global conf
    if conf:
        stop_node()
    os.environ["PATH"] = old_path


def start_node():
    global conf
    global ssh
    global s
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["networks"] = [
        {
            "device": "vmxnet3",
            "id": "mgmt",
            "mac": "00:60:16:9c:50:6a"
        }
    ]
    conf["compute"]["networks"][0]["port_forward"] = [
        {
            "outside": 2222,
            "inside": 22,
            "protocal": "tcp"
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
    ]

    node = model.CNode(conf)
    node.init()
    node.precheck()
    node.start()
    path = os.path.join(node.workspace.get_workspace(), ".monitor")
    s = UnixSocket(path)
    s.connect()
    s.recv()

    payload_enable_qmp = {
        "execute": "qmp_capabilities"
    }

    s.send(json.dumps(payload_enable_qmp))
    s.recv()
    # wait until system is ready for ssh.
    ssh = sshclient.SSH(host="127.0.0.1", username="root", password="root", port=2222)
    ssh.wait_for_host_up()


def stop_node():
    global s
    global conf
    s.close()
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}


def get_interface_name():
    global inface
    global ssh
    with open("ifg_info.txt", "w+") as ff:
        status, output = ssh.exec_command("ip link")
        ff.write(output)
        ff.seek(0, 0)
        for str0 in ff.readlines():
            if "00:60:16:9c:50:6a" in str0:
                break
            str1 = str0.split()
            # in order to delete ":"
            inface = str1[1][0:-1]
    os.remove('ifg_info.txt')


class nicdata_check:
    Grxstat = 0
    Grxerr = 0
    Gtxstat = 0
    Gtxerr = 0

    def getnicdata(self):
        status, output = ssh.exec_command('ifconfig -s {}'.format(inface))
        with open("ifg_s.txt", "w+") as fd:
            fd.write(output)
            fd.seek(0, 0)
            for line in fd.readlines():
                print(line)
                line1 = line.split()
                if line1[0] == inface:
                    self.Grxstat = long(line1[2])
                    self.Grxerr = long(line1[3])
                    self.Gtxstat = long(line1[6])
                    self.Gtxerr = long(line1[7])
        os.remove('ifg_s.txt')


class test_nic_error_inject(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_status_code_error_inject(self):
        """
        status_code_error: tx rx dir change cmd
        status_code_error_full: full change cmd
        (fdata.Gtxerr + math.ceil(sdata.Gtxstat - fdata.Gtxstat)*ratio ) = sdata.Gtxerr
        """
        status_code_error = {
            "execute": "vmxnet3-inject-stats-error",
            "arguments": {
                "id": "mgmt",
                "dir": None,
                "ratio": None
            }
        }
        status_code_error_full = {
            "execute": "vmxnet3-inject-stats-error",
            "arguments": {
                "id": "mgmt",
                "dir": "full",
                "ratio": 1
            }
        }
        status_code_meter = [
            ["tx", 0.2],
            ["rx", 0.1],
        ]

        get_interface_name()
        # first get raw data
        fdata = nicdata_check()
        fdata.getnicdata()
        self.assertEqual(0, fdata.Gtxerr, "first txerr not 0")
        self.assertEqual(0, fdata.Grxerr, "first rxerr not 0")

        # second change ratio
        for status_code_meters in status_code_meter:
            status_code_error["arguments"]["dir"] = status_code_meters[0]
            status_code_error["arguments"]["ratio"] = status_code_meters[1]
            s.send(json.dumps(status_code_error))
            s.recv()
        # sleep 20s for packets in or out and get changed data
        time.sleep(20)
        sdata = nicdata_check()
        sdata.getnicdata()
        self.assertEqual(sdata.Grxerr, long(math.ceil(sdata.Grxstat * 0.1)), "rxerr ratio not ok")
        self.assertEqual(sdata.Gtxerr, long(math.ceil(sdata.Gtxstat * 0.2)), "txerr ratio not ok")
        # third check next ratio
        s.send(json.dumps(status_code_error_full))
        s.recv()
        time.sleep(20)

        tdata = nicdata_check()
        tdata.getnicdata()
        newdata = long(math.ceil(sdata.Grxstat * 0.1)) + long(math.ceil(tdata.Grxstat - sdata.Grxstat) * 1)
        self.assertEqual(tdata.Grxerr, newdata)
        newdata = long(math.ceil(sdata.Gtxstat * 0.2)) + long(math.ceil(tdata.Gtxstat - sdata.Gtxstat) * 1)
        self.assertEqual(tdata.Gtxerr, newdata)
