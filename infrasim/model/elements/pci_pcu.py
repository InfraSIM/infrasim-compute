'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIPCU(CElement):
    '''
    PciVmd provides the function related with Intel VolumnManagementDevice.
    Check its parameters and generate argument string.
    '''

    def __init__(self, pcu_info):
        super(CPCIPCU, self).__init__()
        self.__pcu_info = pcu_info
        self.bus = None
        self.id = None
        self.device = "pcu"
        self.pcie_topo = None
        self.spd_data_file = None

    def precheck(self):
        if self.__pcu_info.get("bus") is None:
            raise ArgsNotCorrect("pcu's bus is mandatory!")
        if self.__pcu_info.get("spd_data_file") is None:
            raise ArgsNotCorrect("pcu's spd_data_file is mandatory!")

    def init(self):
        self.bus = self.__pcu_info["bus"]
        self.spd_data_file = self.__pcu_info["spd_data_file"]

    def handle_parms(self):
        args_cr0 = {}
        args_cr0["bus"] = self.bus
        args_cr0["id"] = "pcu-cr0-{}".format(self.bus)
        args_cr0["addr"] = "1e.0"
        args_cr0["multifunction"] = "on"
        cr0_list = []
        cr0_list.append("-device pcu_cr0")

        for k, v in args_cr0.items():
            cr0_list.append("{}={}".format(k, v))

        self.add_option(",".join(cr0_list))

        args_cr5 = {}
        args_cr5["bus"] = self.bus
        args_cr5["id"] = "pcu-cr5-{}".format(self.bus)
        args_cr5["addr"] = "1e.5"
        args_cr5["spd_data_file"] = self.spd_data_file
        cr5_list = []
        cr5_list.append("-device pcu_cr5")

        for m, n in args_cr5.items():
            cr5_list.append("{}={}".format(m, n))

        self.add_option(",".join(cr5_list))
