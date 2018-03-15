'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

from infrasim.model.core.task import Task
from infrasim.log import infrasim_log
from infrasim.workspace import ChassisWorkspace


class CChassisDaemon(Task):
    '''
    start/stop /usr/local/bin/infrasim-chassis
    '''
    def __init__(self, chassis_name, file_name):
        super(CChassisDaemon, self).__init__()
        self.__bin = "infrasim-chassis"
        self.__chassis_name = chassis_name
        self.logger = infrasim_log.get_chassis_logger(chassis_name)
        self.__file_name = file_name

    def get_commandline(self):
        chassis_str = "{} {} {}".\
            format(self.__bin,
                   self.__chassis_name,
                   self.__file_name)
                  
        return chassis_str

    def init(self, workspace):
        self.set_workspace(workspace)
        self.set_task_name(self.__chassis_name)
        
    def start(self):
        self.run()

    def status(self):
        pass
            
