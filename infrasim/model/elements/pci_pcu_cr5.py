'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIPCU_CR5(CElement):
    '''
    PciVmd provides the function related with Intel VolumnManagementDevice.
    Check its parameters and generate argument string.
    '''

    def __init__(self, pcu_info):
        super(CPCIPCU_CR5, self).__init__()
        self.__pcu_info = pcu_info
        self.bus = None
        self.id = None
        self.device = "pcu_cr5"
        self.pcie_topo = None
        self.spd_data_file = None

    def precheck(self):
        if self.__pcu_info.get("bus") is None:
            raise ArgsNotCorrect("pcu-cr5 bus is mandatory!")
        if self.__pcu_info.get("id") is None:
            raise ArgsNotCorrect("pcu-cr5's id is mandatory!")
        if self.__pcu_info.get("spd_data_file") is None:
            raise ArgsNotCorrect("pcu-cr5's spd_data_file is mandatory!")

    def init(self):
        self.bus = self.__pcu_info["bus"]
        self.id = self.__pcu_info["id"]
        self.spd_data_file = self.__pcu_info["spd_data_file"]

    def handle_parms(self):
        args = {}
        args["bus"] = self.bus
        args["addr"] = "1e.5"
        args["id"] = self.id
        args["spd_data_file"] = self.spd_data_file
        opt_list = []

        opt_list.append("-device pcu_cr5")
        for k, v in args.items():
            opt_list.append("{}={}".format(k, v))

        self.add_option(",".join(opt_list))
