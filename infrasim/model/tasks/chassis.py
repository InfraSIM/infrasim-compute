'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

from infrasim.chassis.dataset import DataSet
from infrasim import ArgsNotCorrect, config, chassis
from infrasim import helper
from infrasim.model.core.task import Task
from infrasim.model.core.node import CNode
from infrasim.workspace import ChassisWorkspace
from infrasim.log import infrasim_log


class CChassis(Task):
    '''
    start /usr/local/bin/infrasim-chassis
    start sub nodes.
    
    stop sub nodes.
    stop /usr/local/bin/infrasim-chassis
    '''
    def __init__(self, chassis_name="default", chassis_info=None):
        super(CChassis, self).__init__()

        self.__bin = "infrasim-chassis"

        self.__chassis_name = chassis_name
        self.__chassis = chassis_info
        self.logger = infrasim_log.get_chassis_logger(chassis_name)
        self.__dataset = DataSet(chassis_name)
        self.__node_list = {}
        self.__file_name = "/tmp/{}_chassis_data.bin".format(chassis_name)
                          
    def set_chassis_name(self, name):
        self.__chassis_name = name

    def get_commandline(self):
        chassis_str = "{} {} {}".\
            format(self.__bin,
                   self.__chassis_name,
                   self.__file_name)
                  
        return chassis_str
        
    options = {
        "precheck": CNode.precheck,
        "init": CNode.init,
        "start": CNode.start,
        "stop": CNode.stop,
        "destroy": CNode.terminate_workspace
    }

    def process_by_node_names(self, action, *args):
        node_names = list(args) or self.__node_list.keys()
        all_node_names = set(self.__node_list.keys())
        selected_node_names = all_node_names.intersection(set(node_names))
        for name in selected_node_names:
            self.options[action](self.__node_list[name])

    def precheck(self, *args):
        # check total resources
        self.process_by_node_names("precheck", *args)

    def init(self, *args):
        self.workspace = ChassisWorkspace(self.__chassis)
        if not self.__is_running():
            self.workspace.init()
        self.set_workspace(self.workspace.get_workspace())
        self.set_task_name(self.__chassis_name)
        
        for node in self.__chassis['nodes']:
            node_obj = CNode(node)
            node_obj.set_node_name(node["name"])
            self.__node_list[node["name"]] = node_obj
        self.process_by_node_names("init", *args)

    def start(self, *args):
        self.__process_chassis_device()
        self.__dataset.load()
        self.__dataset.fill(self.__file_name)
        self.run()
        self.__create_namespace()
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
            
    def __create_namespace(self):
        self.logger.info("Prepare namespace for each nodes.")
        pass
    
    def __process_chassis_device(self):
        '''
        assign IDs of shared devices
        merge shared device to node.
        '''
        self.logger.info("Assign ShareMemoryId for shared device.")
        for devices in self.__chassis.get('shared_device', {}):
            pass
            
            
