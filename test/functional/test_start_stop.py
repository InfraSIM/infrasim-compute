'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import unittest
import os
from infrasim import model
from infrasim import config
from infrasim import run_command
from test import fixtures
from infrasim.workspace import Workspace

old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


def setup_module():
    os.environ["PATH"] = new_path


def teardown_module():
    os.environ["PATH"] = old_path


def check_node_start_workspace(node_name):

    conf = Workspace.get_node_info_in_workspace(node_name)
    node_root = os.path.join(config.infrasim_home, conf["name"])

    # Check node data folder and files exist
    node_type = conf["type"]
    data_folder = os.path.join(node_root, "data")
    node_emu = os.path.join(data_folder, "{}.emu".format(node_type))
    node_bios = os.path.join(data_folder, "{}_smbios.bin".format(node_type))
    assert os.path.exists(data_folder) is True
    assert os.path.exists(node_emu) is True
    assert os.path.exists(node_bios) is True

    # Check node script folder and files exist
    script_folder = os.path.join(node_root, "script")
    script_chassiscontrol = os.path.join(script_folder, "chassiscontrol")
    script_lancontrol = os.path.join(script_folder, "lancontrol")
    script_startcmd = os.path.join(script_folder, "startcmd")
    script_stopcmd = os.path.join(script_folder, "stopcmd")
    script_resetcmd = os.path.join(script_folder, "resetcmd")
    assert os.path.exists(script_folder) is True
    assert os.path.exists(script_chassiscontrol) is True
    assert os.path.exists(script_lancontrol) is True
    assert os.path.exists(script_startcmd) is True
    assert os.path.exists(script_stopcmd) is True
    assert os.path.exists(script_resetcmd) is True

    # Check etc folder and files exist
    etc_folder = os.path.join(node_root, "etc")
    etc_infrasim_yml = os.path.join(etc_folder, "infrasim.yml")
    etc_vbmc_conf = os.path.join(etc_folder, "vbmc.conf")
    assert os.path.exists(etc_folder) is True
    assert os.path.exists(etc_infrasim_yml) is True
    assert os.path.exists(etc_vbmc_conf) is True

    # Check disk image exist
    node_name = conf["name"]
    node_drive = conf['compute']['storage_backend'][0]['controller']['drives']
    for i in range(1, len(node_drive) + 1):
        disk_file = os.path.join(node_root, "sd{0}.img".format(chr(96 + i)))
        assert os.path.exists(disk_file) is True

    # Check serial device exist
    serial_dev = os.path.join(node_root, ".pty0")
    assert os.path.exists(serial_dev) is True

    # Check unix socket file
    serial = os.path.join(node_root, ".serial")
    assert os.path.exists(serial) is True

    # Check node runtime pid file exist
    node_socat = os.path.join(node_root, ".{}-socat.pid".format(node_name))
    node_ipmi = os.path.join(node_root, ".{}-bmc.pid".format(node_name))
    node_qemu = os.path.join(node_root, ".{}-node.pid".format(node_name))
    assert os.path.exists(node_socat) is True
    assert os.path.exists(node_ipmi) is True
    assert os.path.exists(node_qemu) is True


def check_node_stop_workspace(node_name):

    conf = Workspace.get_node_info_in_workspace(node_name)
    node_root = os.path.join(config.infrasim_home, conf["name"])

    # Check node data folder and files exist
    node_type = conf["type"]
    data_folder = os.path.join(node_root, "data")
    node_emu = os.path.join(data_folder, "{}.emu".format(node_type))
    node_bios = os.path.join(data_folder, "{}_smbios.bin".format(node_type))
    assert os.path.exists(data_folder) is True
    assert os.path.exists(node_emu) is True
    assert os.path.exists(node_bios) is True

    # Check node script folder and files exist
    script_folder = os.path.join(node_root, "script")
    script_chassiscontrol = os.path.join(script_folder, "chassiscontrol")
    script_lancontrol = os.path.join(script_folder, "lancontrol")
    script_startcmd = os.path.join(script_folder, "startcmd")
    script_stopcmd = os.path.join(script_folder, "stopcmd")
    script_resetcmd = os.path.join(script_folder, "resetcmd")
    assert os.path.exists(script_folder) is True
    assert os.path.exists(script_chassiscontrol) is True
    assert os.path.exists(script_lancontrol) is True
    assert os.path.exists(script_startcmd) is True
    assert os.path.exists(script_stopcmd) is True
    assert os.path.exists(script_resetcmd) is True

    # Check etc folder and files exist
    etc_folder = os.path.join(node_root, "etc")
    etc_infrasim_yml = os.path.join(etc_folder, "infrasim.yml")
    etc_vbmc_conf = os.path.join(etc_folder, "vbmc.conf")
    assert os.path.exists(etc_folder) is True
    assert os.path.exists(etc_infrasim_yml) is True
    assert os.path.exists(etc_vbmc_conf) is True

    # Check disk image exist
    node_name = conf["name"]
    node_stor = conf['compute']['storage_backend']
    disk_index = 0
    for stor_control in node_stor:
        for drive in stor_control:
            disk_file = os.path.join(node_root, "sd{0}.img".format(chr(97 + disk_index)))
            disk_index += 1
            assert os.path.exists(disk_file) is True

    # Check serial device exist
    serial_dev = os.path.join(node_root, ".pty0")
    assert os.path.exists(serial_dev) is False

    # Check unix socket file
    serial = os.path.join(node_root, ".serial")
    assert os.path.exists(serial) is False

    # Check node runtime pid file don't exist
    node_socat = os.path.join(node_root, ".{}-socat.pid".format(node_name))
    node_ipmi = os.path.join(node_root, ".{}-bmc.pid".format(node_name))
    node_qemu = os.path.join(node_root, ".{}-node.pid".format(node_name))
    assert os.path.exists(node_socat) is False
    assert os.path.exists(node_ipmi) is False
    assert os.path.exists(node_qemu) is False


class test_control_by_lib(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()
        cls.node_root = os.path.join(config.infrasim_home, cls.conf["name"])

    @classmethod
    def tearDownClass(cls):
        node = model.CNode(cls.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.conf = None

    def test_lib_start_stop(self):
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()

        # Check workspace
        check_node_start_workspace(self.conf["name"])

        # Check node runtime pid file exist
        node_name = self.conf["name"]
        node_socat = os.path.join(self.node_root, ".{}-socat.pid".format(node_name))
        node_ipmi = os.path.join(self.node_root, ".{}-bmc.pid".format(node_name))
        node_qemu = os.path.join(self.node_root, ".{}-node.pid".format(node_name))
        self.assertTrue(os.path.exists(node_socat))
        self.assertTrue(os.path.exists(node_ipmi))
        self.assertTrue(os.path.exists(node_qemu))

        # Check node runtime process exist
        with open(node_socat, 'r') as fp:
            pid_socat = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_socat)))
        with open(node_ipmi, 'r') as fp:
            pid_ipmi = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_ipmi)))
        with open(node_qemu, 'r') as fp:
            pid_qemu = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_qemu)))

        node = model.CNode(self.conf)
        node.init()
        node.stop()

        # Check workspace
        check_node_stop_workspace(self.conf["name"])

        node.terminate_workspace()

        # Check node runtime pid file don't exist
        self.assertFalse(os.path.exists(node_socat))
        self.assertFalse(os.path.exists(node_ipmi))
        self.assertFalse(os.path.exists(node_qemu))

        # Check node runtime process don't exist any more
        self.assertFalse(os.path.exists("/proc/{}".format(pid_socat)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_ipmi)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_qemu)))


class test_control_by_cli(unittest.TestCase):

    node_name = "default"
    node_workspace = os.path.join(config.infrasim_home, node_name)

    def tearDown(self):
        os.system("infrasim node destroy {}".format(self.node_name))
        os.system("rm -rf {}".format(self.node_workspace))
        os.system("pkill socat")
        os.system("pkill ipmi")
        os.system("pkill qemu")

    def test_normal_start_stop(self):

        run_command("infrasim node start")

        # Check workspace
        check_node_start_workspace(self.node_name)

        # Check node runtime pid file exist
        node_socat = os.path.join(self.node_workspace, ".{}-socat.pid".format(self.node_name))
        node_ipmi = os.path.join(self.node_workspace, ".{}-bmc.pid".format(self.node_name))
        node_qemu = os.path.join(self.node_workspace, ".{}-node.pid".format(self.node_name))
        self.assertTrue(os.path.exists(node_socat))
        self.assertTrue(os.path.exists(node_ipmi))
        self.assertTrue(os.path.exists(node_qemu))

        # Check node runtime process exist
        with open(node_socat, 'r') as fp:
            pid_socat = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_socat)))
        with open(node_ipmi, 'r') as fp:
            pid_ipmi = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_ipmi)))
        with open(node_qemu, 'r') as fp:
            pid_qemu = fp.read()
            self.assertTrue(os.path.exists("/proc/{}".format(pid_qemu)))

        run_command("infrasim node stop")

        # Check workspace
        check_node_stop_workspace(self.node_name)

        # Check node runtime pid file don't exist
        self.assertFalse(os.path.exists(node_socat))
        self.assertFalse(os.path.exists(node_ipmi))
        self.assertFalse(os.path.exists(node_qemu))

        # Check node runtime process don't exist any more
        self.assertFalse(os.path.exists("/proc/{}".format(pid_socat)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_ipmi)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_qemu)))

        run_command("infrasim node destroy")

        # Check node runtime pid file don't exist
        self.assertFalse(os.path.exists(node_socat))
        self.assertFalse(os.path.exists(node_ipmi))
        self.assertFalse(os.path.exists(node_qemu))

        # Check node runtime process don't exist any more
        self.assertFalse(os.path.exists("/proc/{}".format(pid_socat)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_ipmi)))
        self.assertFalse(os.path.exists("/proc/{}".format(pid_qemu)))
