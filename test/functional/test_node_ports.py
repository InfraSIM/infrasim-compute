import unittest
import subprocess
import time
import os
from nose.tools import raises, assert_raises
from test import fixtures
from infrasim import model
from infrasim import ArgsNotCorrect, run_command
import threading
from infrasim import ipmiconsole

PS_QEMU = "ps ax | grep qemu"
PS_IPMI = "ps ax | grep ipmi"
PS_SOCAT = "ps ax | grep socat"
PS_RACADM = "ps ax | grep racadmsim"
old_path = os.environ.get("PATH")
new_path = "{}/bin:{}".format(os.environ.get("PYTHONPATH"), old_path)


class test_node_ports(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.node_info = fake_config.get_node_info()

    def tearDown(self):
        node = model.CNode(self.node_info)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.node_info = None
        os.environ["PATH"] = old_path

    @raises(ArgsNotCorrect)
    def test_qemu_ipmi_port_in_use(self):
        node = model.CNode(self.node_info)
        node.init()
        node.precheck()
        node.start()

        # precheck again, there should be exception thrown
        for task in node.get_task_list():
            if isinstance(task, model.CBMC):
                task.precheck()
                break

    @raises(ArgsNotCorrect)
    def test_vnc_port_in_use(self):
        node = model.CNode(self.node_info)
        node.init()
        node.precheck()
        node.start()
        # wait qemu up
        time.sleep(2)

        for task in node.get_task_list():
            if isinstance(task, model.CCompute):
                task.precheck()
                break

    def test_start_node1_then_start_node2(self):
        self.node_info['name'] = "test1"
        node1 = model.CNode(self.node_info)
        node1.init()
        node1.precheck()
        node1.start()
        time.sleep(2)

        self.node_info['name'] = "test2"
        node2 = model.CNode(self.node_info)
        node2.init()
        assert_raises(ArgsNotCorrect, node2.precheck)
        node1.stop()
        node1.terminate_workspace()
        node2.terminate_workspace()


class test_node_ports_no_conflict(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        fake_config_2 = fixtures.FakeConfig()
        self.node_info = fake_config.get_node_info()
        self.node_info_2 = fake_config_2.get_node_info()
        os.environ["PATH"] = new_path

    def tearDown(self):
        node = model.CNode(self.node_info)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.node_info = None

        node = model.CNode(self.node_info_2)
        node.init()
        node.stop()
        node.terminate_workspace()
        self.node_info_2 = None

    def test_start_node1_then_start_node2_no_conflict_ports(self):
        # start node test1
        self.node_info['name'] = "test1"
        node1 = model.CNode(self.node_info)
        node1.init()
        node1.precheck()
        node1.start()
        time.sleep(2)
        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]

        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result

        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_ssh'] = 9301
        self.node_info_2['ipmi_console_port'] = 9001
        self.node_info_2['bmc_connection_port'] = 9101
        if 'dell' in self.node_info_2['type']:
            self.node_info_2['racadm'] = {}
            self.node_info_2['racadm']['port'] = 10023
        self.node_info_2['compute']['vnc_display'] = 2
        self.node_info_2['compute']['monitor'] = {
            'mode': 'readline',
            'chardev': {
                'backend': 'socket',
                'host': '127.0.0.1',
                'port': 2346,
                'server': True,
                'wait': False
            }
        }

        node2 = model.CNode(self.node_info_2)
        node2.init()
        node2.precheck()
        node2.start()
        time.sleep(2)
        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info_2['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]

        # node test1 and test2 should be running simultaneously

        assert "test1" in socat_result and "test2" in socat_result
        assert "test1" in ipmi_result and "test2" in ipmi_result
        assert "test1-node" in qemu_result and "test2-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result and "test2" in racadm_result


class test_start_node_with_conflict_port(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["PATH"] = new_path
        fake_config = fixtures.FakeConfig()
        cls.node_info = fake_config.get_node_info()

        # start node test1
        cls.node_info['name'] = "test1"
        node1 = model.CNode(cls.node_info)
        node1.init()
        node1.precheck()
        node1.start()
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        node = model.CNode(cls.node_info)
        node.init()
        node.stop()
        node.terminate_workspace()
        cls.node_info = None
        os.environ["PATH"] = old_path

    def setUp(self):
        fake_config_2 = fixtures.FakeConfig()
        self.node_info_2 = fake_config_2.get_node_info()

    def tearDown(self):
        node2 = model.CNode(self.node_info_2)
        node2.init()
        node2.stop()
        node2.terminate_workspace()

    def test_start_node_with_conflict_bmc_connection_port(self):
        """
        Port test: after node1 start, if node2 also use the same bmc_connection_port to start, it won't start
        """

        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]
        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result

        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_ssh'] = 9301
        self.node_info_2['ipmi_console_port'] = 9001
        if 'dell' in self.node_info_2['type']:
            self.node_info_2['racadm'] = {}
            self.node_info_2['racadm']['port'] = 10023
        # self.node_info_2['bmc_connection_port'] = 9101
        self.node_info_2['compute']['vnc_display'] = 2
        self.node_info_2['compute']['monitor'] = {
            'mode': 'readline',
            'chardev': {
                'backend': 'socket',
                'host': '127.0.0.1',
                'port': 2346,
                'server': True,
                'wait': False
            }
        }

        try:
            node2 = model.CNode(self.node_info_2)
            node2.init()
            node2.precheck()
        except ArgsNotCorrect, e:
            assert "Port 9002 is already in use." in e.value
            assert True
        else:
            assert False

    def test_start_node_with_conflict_VNC_port(self):
        """
        Port test: after node1 start, if node2 also use the same VNC_port to start, it won't start
        """

        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]

        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result
        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_ssh'] = 9301
        self.node_info_2['ipmi_console_port'] = 9001
        self.node_info_2['bmc_connection_port'] = 9101
        # self.node_info_2['compute']['vnc_display'] = 2
        self.node_info_2['compute']['monitor'] = {
            'mode': 'readline',
            'chardev': {
                'backend': 'socket',
                'host': '127.0.0.1',
                'port': 2346,
                'server': True,
                'wait': False
            }
        }

        try:
            node2 = model.CNode(self.node_info_2)
            node2.init()
            node2.precheck()
        except ArgsNotCorrect, e:
            assert "VNC port 5901 is already in use." in e.value
            assert True
        else:
            assert False

    def test_start_node_with_conflict_monitor_port(self):
        """
        Port test: after node1 start, if node2 also use the same monitor_port to start, it won't start
        """

        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]
        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result

        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_ssh'] = 9301
        self.node_info_2['ipmi_console_port'] = 9001
        self.node_info_2['bmc_connection_port'] = 9101
        if 'dell' in self.node_info_2['type']:
            self.node_info_2['racadm'] = {}
            self.node_info_2['racadm']['port'] = 10023
        self.node_info_2['compute']['vnc_display'] = 2

        try:
            node2 = model.CNode(self.node_info_2)
            node2.init()
            node2.precheck()
        except ArgsNotCorrect, e:
            assert "Port 2345 is already in use" in e.value
        else:
            assert False

    def test_start_node_with_conflict_ipmi_console_port(self):
        """
        Port test: after node1 start, if node2 also use the same ipmi_console_port to start, it won't start
        """

        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]
        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result

        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_ssh'] = 9301
        self.node_info_2['bmc_connection_port'] = 9101
        if 'dell' in self.node_info_2['type']:
            self.node_info_2['racadm'] = {}
            self.node_info_2['racadm']['port'] = 10023
        self.node_info_2['compute']['vnc_display'] = 2
        self.node_info_2['compute']['monitor'] = {
            'mode': 'readline',
            'chardev': {
                'backend': 'socket',
                'host': '127.0.0.1',
                'port': 2346,
                'server': True,
                'wait': False
            }
        }

        try:
            node2 = model.CNode(self.node_info_2)
            node2.init()
            node2.precheck()
        except ArgsNotCorrect, e:
            assert "Port 9000 is already in use." in e.value
            assert True
        else:
            assert False

    def test_start_node_with_conflict_ipmi_console_ssh_port(self):
        """
        Port test: after node1 start, if node2 also use the same ipmi_console_ssh_port to start, it won't start
        """

        socat_result = run_command(PS_SOCAT, True,
                                   subprocess.PIPE, subprocess.PIPE)[1]
        ipmi_result = run_command(PS_IPMI, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        qemu_result = run_command(PS_QEMU, True,
                                  subprocess.PIPE, subprocess.PIPE)[1]
        if 'dell' in self.node_info['type']:
            racadm_result = run_command(PS_RACADM, True,
                                        subprocess.PIPE, subprocess.PIPE)[1]

        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result
        if 'dell' in self.node_info['type']:
            assert "test1" in racadm_result

        ipmi_console_thread = threading.Thread(
            target=ipmiconsole.start, args=(self.node_info["name"],))
        ipmi_console_thread.setDaemon(True)
        ipmi_console_thread.start()
        time.sleep(20)

        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_port'] = 9001
        self.node_info_2['bmc_connection_port'] = 9101
        if 'dell' in self.node_info_2['type']:
            self.node_info_2['racadm'] = {}
            self.node_info_2['racadm']['port'] = 10023
        self.node_info_2['compute']['vnc_display'] = 2
        self.node_info_2['compute']['monitor'] = {
            'mode': 'readline',
            'chardev': {
                'backend': 'socket',
                'host': '127.0.0.1',
                'port': 2346,
                'server': True,
                'wait': False
            }
        }

        node2 = model.CNode(self.node_info_2)
        node2.init()
        node2.precheck()
        node2.start()
        # FIXME: Sleep is not a good way to wait for vbmc start
        time.sleep(5)

        ipmi_console_cmd = "sudo ipmi-console start test2"
        self.assertRaises(
            Exception, run_command, cmd=ipmi_console_cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        ipmiconsole.stop(self.node_info["name"])
        node2.stop()
