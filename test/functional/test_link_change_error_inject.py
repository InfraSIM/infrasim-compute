'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import json
import time
import base64
from infrasim import model
from infrasim.helper import UnixSocket
from infrasim import sshclient
from test import fixtures


conf = {}
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)
inface = " "
QEMU_PATH = "https://bintray.com/infrasim/deb/download_file?file_path\
=infrasim-qemu_2.10.1-ubuntu-xenial-1.0.239_amd64.deb"


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
    global sg
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["compute"]["guest-agent"] = True
    conf["compute"]["networks"] = [
        {
            "device": "e1000",
            "id": "e1000.0",
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
    conf["compute"]["guest-agent"] = True

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
    # second sg: unixsocket guest.agt
    path_guestagt = os.path.join(node.workspace.get_workspace(), "guest.agt")
    sg = UnixSocket(path_guestagt)
    sg.connect()

    payload_test_ping = {
        "execute": "guest-ping"
    }

    sg.send(json.dumps(payload_test_ping))

    # wait until system is ready for ssh.
    ssh = sshclient.SSH(host="127.0.0.1", username="root", password="root", port=2222)
    ssh.wait_for_host_up()


def stop_node():
    global s
    global sg
    global conf
    s.close()
    sg.close()
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


def guest_exec_cmd_step(cmd_exec, cmd_status, sfd):

    sfd.send(json.dumps(cmd_exec))
    # wait for data all
    time.sleep(1)
    teststr = json.loads(sfd.recv())
    cmd_status["arguments"]["pid"] = teststr["return"]["pid"]

    sfd.send(json.dumps(cmd_status))
    stest = ""
    tcount = 0
    while True:
        tcount += 1
        time.sleep(1)
        rdata = ""
        rdata = sfd.recv()
        stest += rdata
        if ("\"exited\": true" in stest) or (tcount > 100):
            break

    teststr1 = json.loads(stest)
    ifdata = (teststr1.get('return')).get("out-data")
    pidinfo = base64.b64decode(ifdata)
    print(pidinfo)

    return pidinfo


class test_link_status_error_inject(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_node()

    @classmethod
    def tearDownClass(cls):
        stop_node()

    def test_status_code_error_inject(self):
        status_code_error1 = {
            "execute": "set_link",
            "arguments": {
                "name": "e1000.0",
                "up": False
            }
        }
        status_code_error2 = {
            "execute": "set_link",
            "arguments": {
                "name": "e1000.0",
                "up": True
            }
        }
        guest_cmd_ifconfig = {
            "execute": "guest-exec",
            "arguments": {
                "path": "/sbin/ifconfig",
                "capture-output": True
            }
        }
        guest_cmd_pid = {
            "execute": "guest-exec-status",
            "arguments": {
                "pid": None
            }
        }

        # defore link down interface ,use ssh do some prepare works
        get_interface_name()
        status, output = ssh.exec_command(" ifconfig")
        self.assertIn("{}: flags=4163".format(inface), output, "system start and interface down ")

        status, output = ssh.exec_command(" wget {} -O infrasim-qemu_2.10.1-ubuntu.deb".format(QEMU_PATH))
        self.assertFalse(status)
        status, output = ssh.exec_command(" sudo dpkg -i infrasim-qemu_2.10.1-ubuntu.deb")
        self.assertFalse(status)

        status, output = ssh.exec_command(" rm  infrasim-qemu_2.10.1-ubuntu.deb")
        self.assertFalse(status)
        status, output = ssh.exec_command(" touch qemu-ga.pid")
        self.assertFalse(status)
        status, output = ssh.exec_command(" sudo qemu-ga -m isa-serial -p /dev/ttyS3 -t /tmp -f qemu-ga.pid -d")
        self.assertFalse(status)
        # down interface and get status
        s.send(json.dumps(status_code_error1))
        s.recv()
        # must wait for cmd exec ok ,otherwise the status will not right
        count = 0
        while ssh.connected():
            time.sleep(1)
            self.assertNotEqual(5, count, "link down operation did't work")
            count += 1

        ifginfo = guest_exec_cmd_step(guest_cmd_ifconfig, guest_cmd_pid, sg)
        self.assertIn("{}: flags=4099".format(inface), ifginfo, "set link down fail")
        # set interface up and get status
        s.send(json.dumps(status_code_error2))
        s.recv()

        count = 0
        while not ssh.connect():
            time.sleep(1)
            self.assertNotEqual(5, count, "link up operation did't work")
            count += 1

        ifginfo = guest_exec_cmd_step(guest_cmd_ifconfig, guest_cmd_pid, sg)
        self.assertIn("{}: flags=4163".format(inface), ifginfo, "set link up fail")
