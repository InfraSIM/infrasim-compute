from test.fixtures import FakeConfig
from infrasim import run_command
from infrasim.model import CNode
import unittest
import time
import os
from nose.tools import assert_raises
from infrasim import ArgsNotCorrect, CommandRunFailed


class test_net_namespace(unittest.TestCase):
    dummy_intf_name = "eth0"

    @classmethod
    def tearDownClass(cls):
        # Trying to clean up the environment
        try:
            _, output = run_command("ip netns")
            netns_list = output.strip().split(os.linesep)
            for netns in netns_list:
                run_command("ip netns delete {}".format(netns))

            run_command("pkill ipmi_sim")
            run_command("pkill socat")
            run_command("pkill qemu-system-x86_64")
        except CommandRunFailed:
            pass

    def _setup_netns(self, netns):
        # Create net namespace "test"
        run_command("ip netns add {}".format(netns))

        command_prefix = "ip netns exec {} ".format(netns)

        # Create a virtual interface in namespace
        run_command("{} ip link add name {} type dummy".format(command_prefix, self.dummy_intf_name))

        # Link up lo device
        run_command("{} ip link set dev lo up".format(command_prefix))

        # Link up dummy interface
        run_command("{} ip link set dev {} up".format(command_prefix, self.dummy_intf_name))

        # Add IP address for this dummy interface
        run_command("{} ip address add 10.0.2.10/24 dev {}".format(command_prefix, self.dummy_intf_name))

    def _teardown_netns(self, netns):
        run_command("ip netns delete {}".format(netns))

    def _verify_node_in_netns(self, node_obj, netns):
        for task in node_obj.get_task_list():
            pid = task.get_task_pid()
            _, output = run_command("ip netns identify {}".format(pid))
            assert netns in output

    def _start_node(self, node_info):
        fake_node_obj = CNode(node_info)
        fake_node_obj.init()
        try:
            fake_node_obj.precheck()
            fake_node_obj.start()
        except Exception as e:
            raise e
        return fake_node_obj

    def _stop_node(self, node_obj):
        node_obj.stop()
        node_obj.terminate_workspace()

    def test_one_node_runnning_in_one_net_namespace(self):
        # create netns
        self._setup_netns("test")
        fake_node = FakeConfig().get_node_info()
        fake_node["name"] = "test"
        fake_node["namespace"] = "test"
        fake_node_obj = self._start_node(fake_node)
        time.sleep(2)

        self._verify_node_in_netns(fake_node_obj, "test")

        self._stop_node(fake_node_obj)
        self._teardown_netns("test")

    def test_two_nodes_running_in_different_net_namespace(self):
        self._setup_netns("test1")
        self._setup_netns("test2")

        fake_node1 = FakeConfig().get_node_info()
        fake_node1["name"] = "test1"
        fake_node1["namespace"] = "test1"
        fake_node_obj_1 = self._start_node(fake_node1)

        fake_node2 = FakeConfig().get_node_info()
        fake_node2["name"] = "test2"
        fake_node2["namespace"] = "test2"
        fake_node_obj_2 = self._start_node(fake_node2)

        time.sleep(2)

        self._verify_node_in_netns(fake_node_obj_1, "test1")
        self._verify_node_in_netns(fake_node_obj_2, "test2")

        self._stop_node(fake_node_obj_1)
        self._stop_node(fake_node_obj_2)

        self._teardown_netns("test1")
        self._teardown_netns("test2")

    def test_two_nodes_running_in_same_net_namespace(self):
        self._setup_netns("test")
        fake_node1 = FakeConfig().get_node_info()
        fake_node1["name"] = "test1"
        fake_node1["namespace"] = "test"
        fake_node_obj_1 = self._start_node(fake_node1)

        fake_node2 = FakeConfig().get_node_info()
        fake_node2["name"] = "test2"
        fake_node2["namespace"] = "test"
        assert_raises(ArgsNotCorrect, self._start_node, fake_node2)
        self._stop_node(fake_node_obj_1)
        self._teardown_netns("test")

    def test_one_node_running_in_two_different_net_namespace(self):
        self._setup_netns("test1")
        self._setup_netns("test2")

        fake_node = FakeConfig().get_node_info()
        fake_node["name"] = "test"
        fake_node["namespace"] = "test1"
        fake_node_obj_1 = self._start_node(fake_node)
        time.sleep(1)

        fake_node["namespace"] = "test2"
        fake_node_obj_2 = CNode(fake_node)
        fake_node_obj_2.precheck()
        for task in fake_node_obj_2.get_task_list():
            assert task.get_task_pid() > 0

        self._stop_node(fake_node_obj_1)
        self._teardown_netns("test1")
        self._teardown_netns("test2")
