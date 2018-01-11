'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim import ArgsNotCorrect
from infrasim import helper
from infrasim.helper import run_in_namespace
from infrasim.model.core.task import Task


class CMonitor(Task):
    def __init__(self, monitor_info):
        super(CMonitor, self).__init__()

        self.__bin = "infrasim-monitor"

        self.__monitor_info = monitor_info

        self.__node_name = "default"
        self.__interface = ""
        self.__ip = ""
        self.__port = ""

        self.logger = None

    def precheck(self):
        if not helper.is_valid_ip(self.__ip):
            self.logger.exception("[Monitor] Invalid IP: {} of interface: {}".
                                  format(self.__ip, self.__interface))
            raise ArgsNotCorrect("Invalid IP: {} of interface: {}".format(
                self.__ip, self.__interface))

        if helper.check_if_port_in_use(self.__ip, self.__port):
            self.logger.exception("[Monitor] Monitor port {}:{} is already in use.".
                                  format(self.__ip, self.__port))
            raise ArgsNotCorrect("Monitor port {}:{} is already in use.".
                                 format(self.__ip, self.__port))

    @run_in_namespace
    def init(self):
        if self.__monitor_info.get("interface", None):
            self.__interface = self.__monitor_info.get("interface", None)
            self.__ip = helper.get_interface_ip(self.__interface)
        else:
            self.__ip = "0.0.0.0"
        self.__port = self.__monitor_info.get("port", 9005)

    def set_node_name(self, name):
        self.__node_name = name

    def get_commandline(self):
        monitor_str = "{} {} {} {}".\
            format(self.__bin,
                   self.__node_name,
                   self.__ip,
                   self.__port)
        return monitor_str
