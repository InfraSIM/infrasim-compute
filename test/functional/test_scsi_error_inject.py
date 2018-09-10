'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
import os
import yaml
import json
import re
from infrasim import model
from infrasim.helper import UnixSocket
from infrasim import sshclient
from test import fixtures


file_prefix = os.path.dirname(os.path.realpath(__file__))
page_file = file_prefix + "/fake_page.bin"
test_drive_image = "/tmp/empty_scsi.img"
conf = {}
tmp_conf_file = "/tmp/test.yml"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


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
    global s
    # create a empty image for test.
    os.system("touch {0}".format(test_drive_image))
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    conf["type"] = node_type
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
    global tmp_conf_file
    s.close()
    node = model.CNode(conf)
    node.init()
    node.stop()
    node.terminate_workspace()
    conf = {}
    if os.path.exists(tmp_conf_file):
        os.unlink(tmp_conf_file)
    # remove the empty image for test.
    os.remove(test_drive_image)


@unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
class test_scsi_error_inject(unittest.TestCase):

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def setUpClass(cls):
        start_node(node_type="quanta_d51")

    @classmethod
    @unittest.skipIf(os.environ.get('SKIP_TESTS'), "SKIP Test for PR Triggered Tests")
    def tearDownClass(cls):
        stop_node()

    def test_log_page_error_inject(self):
        log_page_meter = [
            ["life_used", 50, None, None, "0x11", "Percentage used endurance indicator: 0%"],
            ["erase_count", 70, 36862, 4, "0x31", "unknown parameter code = 0x8ffe"],
            ["temperature", 30, 0, 2, "0x0d", "Current temperature = 30"],
            ["temperature", 80, 1, 2, " 0x0d", "Reference temperature = 80"]
        ]
        log_page_error = {
            "execute": "scsi-drive-error-inject",
            "arguments": {
                "id": "dev-scsi0-0-1-0",
                "action": "add"
            }
        }
        for error_meter in log_page_meter:
            log_page_error["arguments"]["type"] = error_meter[0]
            log_page_error["arguments"]["val"] = error_meter[1]
            log_page_error["arguments"]["parameter"] = error_meter[2]
            log_page_error["arguments"]["parameter_length"] = error_meter[3]
            s.send(json.dumps(log_page_error))
            count = 1
            while count < 2:
                try:
                    self.assertEqual(s.recv(), r"(\s)*{\"return\": {}}(\s)*")
                except Exception:
                    count = count + 1
                    s.send(json.dumps(log_page_error))
            status, output = ssh.exec_command("sudo sg_logs /dev/sg1 -p %s" % error_meter[4])
            self.assertIn(error_meter[5], output, "error inject faile")

    def test_defect_data_inject(self):
        defect_data_cmd = {
            "execute": "set-drive-defect",
            "arguments": {
                "id": "dev-scsi0-0-1-0",
                "type": "glist",
                "defect-count": 10
            }
        }
        s.send(json.dumps(defect_data_cmd))
        count = 1
        while count < 2:
            try:
                self.assertEqual(s.recv(), r"(\s)*{\"return\": {}}(\s)*")
            except Exception:
                count = count + 1
                s.send(json.dumps(defect_data_cmd))
        status, output = ssh.exec_command("sudo sginfo /dev/sg1 -d")
        self.assertIn("10 entries (80 bytes)", output, "defect data inject faile")

    def test_status_code_error_inject(self):
        status_code_error = {
            "execute": "scsi-status-code-error-inject",
            "arguments": {
                "id": "dev-scsi0-0-1-0",
                "error_type": None,
                "count": None
            }
        }
        status_code_meter = [
            ["busy", 10000, "busy"],
            ["task-set-full", 10000, "task-set-full"],
            ["task-aborted", 1, "task-aborted"],
            ["check-condition", 1, {"key": 5, "asc": 32, "ascq": 0}, "check-condition"],
            ["check-condition", 1, {"key": 3, "asc": 17, "ascq": 0}, "medium/hardware error"]
        ]

        for status_code_meters in status_code_meter:
            status_code_error["arguments"]["error_type"] = status_code_meters[0]
            status_code_error["arguments"]["count"] = status_code_meters[1]
            if len(status_code_meters) == 4:
                status_code_error["arguments"]["sense"] = status_code_meters[2]
            s.send(json.dumps(status_code_error))
            count = 1
            while count < 2:
                try:
                    self.assertEqual(s.recv(), r"(\s)*{\"return\": {}}(\s)*")
                except Exception:
                    count = count + 1
                    s.send(json.dumps(status_code_error))
            status, output = ssh.exec_command("sudo sg_read if=/dev/sg1 count=512 bs=512")
            reobj = re.search(" ".join(status_code_meters[-1].split("-")), output, re.I)
            assert reobj
