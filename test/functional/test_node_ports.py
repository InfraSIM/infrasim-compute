import unittest
from test import fixtures
from infrasim import model
from infrasim import ArgsNotCorrect
from nose.tools import raises
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
