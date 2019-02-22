'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import json
from infrasim import model
from infrasim.helper import UnixSocket, prepare_ssh, ssh_exec, ssh_close
from test import fixtures
from time import sleep


old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    stop_node()
    os.environ["PATH"] = old_path


conf = None
target_mac = "00:60:16:9c:50:6a"
s = None


def start_node():
    global conf
    global ssh
    global s
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()

    conf["compute"]["networks"] = [
        {
            "device": "e1000",
            "id": "e1000.0",
            "mac": "00:60:16:9c:ff:6a",
            "network_mode": "nat",
            "port_forward": [
                {
                    "outside": 2222,
                    "inside": 22,
                    "protocal": "tcp"
                }
            ]
        },
        {
            "device": "e1000",
            "id": "e1000.1",
            "network_mode": "nat",
            "mac": target_mac,
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
    # first s : unixsocket .monitor
    path = os.path.join(node.workspace.get_workspace(), ".monitor")
    s = UnixSocket(path)
    s.connect()
    s.recv()

    payload_enable_qmp = {
        "execute": "qmp_capabilities"
    }

    s.send(json.dumps(payload_enable_qmp))
    s.recv()

    ssh = prepare_ssh()


def stop_node():
    global conf
    if conf is None:
        return
    s.close()
    ssh_close(ssh)
    node = model.CNode(conf)
    node.init()
    node.stop()
    conf = None
    node.terminate_workspace()


def get_interface_name():
    inface = "lo"
    ret = ssh_exec(ssh, "for f in /sys/class/net/*/address; do echo -n $f' '; cat $f; done")
    for line in ret.split('\n'):
        if target_mac in line:
            inface = line.split('/')[4]
            break
    return inface


class test_link_status_error_inject(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_status_code_error_inject(self):
        cmd_nic_down = {
            "execute": "set_link",
            "arguments": {
                "name": "e1000.1",
                "up": False
            }
        }
        cmd_nic_up = {
            "execute": "set_link",
            "arguments": {
                "name": "e1000.1",
                "up": True
            }
        }
        # defore link down interface ,use ssh do some prepare works
        nic_name = get_interface_name()
        print("Found target nic: {}".format(nic_name))
        output = ssh_exec(ssh, "dhclient {}".format(nic_name))
        output = ssh_exec(ssh, "ifconfig {}".format(nic_name))
        print(output)
        self.assertIn(",RUNNING,", output, "NIC {} is not up yet".format(nic_name))

        # down interface and get status
        s.send(json.dumps(cmd_nic_down))
        s.recv()

        # try 10 times,
        for _ in range(0, 10):
            output = ssh_exec(ssh, "ifconfig {}".format(nic_name))
            if ",RUNNING," not in output:
                break
            sleep(1)
        else:
            print(output)
            self.fail("NIC {} is not down".format(nic_name))

        # set interface up and get status
        s.send(json.dumps(cmd_nic_up))
        s.recv()

        for _ in range(0, 10):
            output = ssh_exec(ssh, "ifconfig {}".format(nic_name))
            if ",RUNNING," in output:
                break
            sleep(1)
        else:
            print(output)
            self.fail("NIC {} is not up again".format(nic_name))
