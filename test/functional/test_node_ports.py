import unittest
import subprocess
import time
from nose.tools import raises, assert_raises
from test import fixtures
from infrasim import model
from infrasim import ArgsNotCorrect, run_command


PS_QEMU = "ps ax | grep qemu"
PS_IPMI = "ps ax | grep ipmi"
PS_SOCAT = "ps ax | grep socat"


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
        old_name = self.node_info['name']
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
        # check if node test1 is running
        assert "test1" in socat_result
        assert "test1" in ipmi_result
        assert "test1-node" in qemu_result

        self.node_info_2['name'] = "test2"
        # modify node configuration to resolve port conflict
        self.node_info_2['ipmi_console_ssh'] = 9301
        self.node_info_2['ipmi_console_port'] = 9001
        self.node_info_2['bmc_connection_port'] = 9101
        self.node_info_2['serial_port'] = 9004
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
        # node test1 and test2 should be running simultaneously

        assert "test1" in socat_result and "test2" in socat_result
        assert "test1" in ipmi_result and "test2" in ipmi_result
        assert "test1-node" in qemu_result and "test2-node" in qemu_result

