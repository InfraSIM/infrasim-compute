from model import CNode
from model import NumaCtl


class CChassis(object):
    def __init__(self, chassis_info):
        self.__chassis = chassis_info
        self.__chassis_model = None
        self.__node_list = {}
        self.__numactl_obj = NumaCtl()

    options = {
        "precheck": CNode.precheck,
        "init": CNode.init,
        "start": CNode.start,
        "stop": CNode.stop,
        "destroy": CNode.terminate_workspace
    }

    def process_by_node_names(self,action, *args):
        node_names = list(args) or self.__node_list.keys()
        all_node_names = set(self.__node_list.keys())
        selected_node_names = all_node_names.intersection(set(node_names))
        for name in selected_node_names:
            self.options[action](self.__node_list[name])

    def precheck(self, *args):
        # check total resources
        self.process_by_node_names("precheck", *args)

    def init(self, *args):
        for node in self.__chassis['nodes']:
            node_obj = CNode(node)
            node_obj.set_node_name(node["name"])
            self.__node_list[node["name"]] = node_obj
        self.process_by_node_names("init", *args)

    def start(self, *args):
        self.process_by_node_names("start", *args)

    def stop(self, *args):
        self.process_by_node_names("stop", *args)

    def destroy(self, *args):
        self.init(*args)
        self.stop(*args)
        self.process_by_node_names("destroy", *args)

    def status(self):
        for node_obj in self.__node_list:
            node_obj.status()
