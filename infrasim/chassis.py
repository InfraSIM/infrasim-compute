from model import CNode
from model import NumaCtl


class CChassis(object):
    def __init__(self, chassis_info):
        self.__chassis = chassis_info
        self.__chassis_model = None
        self.__node_list = []
        self.__numactl_obj = NumaCtl()

    def precheck(self):
        # check total resources
        for node in self.__node_list:
            node.precheck()

    def init(self):
        for node in self.__chassis['nodes']:
            node_obj = CNode(node)
            node_obj.set_node_name(self.__chassis['name'])
            self.__node_list.append(node_obj)

        for node_obj in self.__node_list:
            node_obj.init()

    def start(self, node_name=None):
        for node_obj in self.__node_list:
            if node_name and node_obj.get_node_name() == node_name:
                node_obj.start()
                return

        for node_obj in self.__node_list:
            node_obj.start()

    def stop(self, node_name=None):
        for node_obj in self.__node_list:
            if node_name and node_obj.get_node_name() == node_name:
                node_obj.stop()
                return

        for node_obj in self.__node_list:
            node_obj.stop()

    def status(self):
        for node_obj in self.__node_list:
            node_obj.status()
