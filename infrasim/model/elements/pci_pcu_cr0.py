'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIPCU_CR0(CElement):
    '''
    PciVmd provides the function related with Intel VolumnManagementDevice.
    Check its parameters and generate argument string.
    '''

    def __init__(self, pcu_info):
        super(CPCIPCU_CR0, self).__init__()
        self.__pcu_info = pcu_info
        self.bus = None
        self.id = None
        self.device = "pcu_cr0"
        self.pcie_topo = None

    def precheck(self):
        if self.__pcu_info.get("bus") is None:
            raise ArgsNotCorrect("pcu-cr0's bus is mandatory!")
        if self.__pcu_info.get("id") is None:
            raise ArgsNotCorrect("pcu-cr0's id is mandatory!")

    def init(self):
        self.bus = self.__pcu_info["bus"]
        self.id = self.__pcu_info["id"]

    def handle_parms(self):
        args = {}
        args["bus"] = self.bus
        args["multifunction"] = "on"
        args["addr"] = "1e.0"
        args["id"] = self.id
        opt_list = []

        opt_list.append("-device pcu_cr0")
        for k, v in args.items():
            opt_list.append("{}={}".format(k, v))

        self.add_option(",".join(opt_list))
