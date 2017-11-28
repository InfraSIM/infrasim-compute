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


class CRacadm(Task):
    def __init__(self, racadm_info):
        super(CRacadm, self).__init__()

        self.__bin = "racadmsim"

        self.__racadm_info = racadm_info

        self.__node_name = "default"
        self.__port_idrac = 10022
        self.__username = ""
        self.__password = ""
        self.__interface = None
        self.__ip = ""
        self.__data_src = ""

    def precheck(self):
        if not self.__ip:
            raise ArgsNotCorrect("[Racadm] Specified racadm interface {} doesn\'t exist".
                                 format(self.__interface))

        if helper.check_if_port_in_use(self.__ip, self.__port_idrac):
            raise ArgsNotCorrect("[Racadm] Racadm port {}:{} is already in use.".
                                 format(self.__ip,
                                        self.__port_idrac))

    @run_in_namespace
    def init(self):
        if "interface" in self.__racadm_info:
            self.__interface = self.__racadm_info.get("interface", "")
            self.__ip = helper.get_interface_ip(self.__interface)
        else:
            self.__ip = "0.0.0.0"
        self.__port_idrac = self.__racadm_info.get("port", 10022)
        self.__username = self.__racadm_info.get("username", "admin")
        self.__password = self.__racadm_info.get("password", "admin")
        self.__data_src = self.__racadm_info.get("data", "auto")

    def set_node_name(self, name):
        self.__node_name = name

    def get_commandline(self):
        racadmsim_str = "{} {} {} {} {} {} {}".\
            format(self.__bin,
                   self.__node_name,
                   self.__ip,
                   self.__port_idrac,
                   self.__username,
                   self.__password,
                   self.__data_src)
        return racadmsim_str
