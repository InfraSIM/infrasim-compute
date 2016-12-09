import unittest
from test import fixtures
from infrasim import model
from infrasim import ArgsNotCorrect
from nose.tools import raises, assert_raises
import time


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
