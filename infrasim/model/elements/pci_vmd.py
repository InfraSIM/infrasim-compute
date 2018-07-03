'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIVMD(CElement):
    '''
    PciVmd provides the function related with Intel VolumnManagementDevice.
    Check its parameters and generate argument string.
    '''

    def __init__(self, vmd_info):
        super(CPCIVMD, self).__init__()
        self.__vmd_info = vmd_info
        self.__bar1_size = None
        self.__bar2_size = None
        self.bus = None
        self.id = None
        self.device = "vmd"
        self.pcie_topo = None

    def precheck(self):
        if self.__vmd_info.get("id") is None:
            raise ArgsNotCorrect("VMD's id is mandatory!")

        if self.__vmd_info.get("bus") is None:
            raise ArgsNotCorrect("VMD's bus is mandatory!")

        size = self.__vmd_info.get("bar1_size", 1024)
        if (size & (size - 1)) != 0:
            raise ArgsNotCorrect("bar1_size must be pow 2")

        size = self.__vmd_info.get("bar2_size", 1024)
        if (size & (size - 1)) != 0:
            raise ArgsNotCorrect("bar2_size must be pow 2")

    def init(self):
        self.id = self.__vmd_info["id"]
        self.bus = self.__vmd_info["bus"]
        self.__bar1_size = self.__vmd_info.get("bar1_size")
        self.__bar2_size = self.__vmd_info.get("bar2_size")

    def handle_parms(self):
        args = {}
        args["id"] = self.id
        args["bus"] = self.bus
        args["multifunction"] = "on"
        args["addr"] = "5.5"
        if self.__bar1_size:
            args["mbar1_size"] = self.__bar1_size
        if self.__bar2_size:
            args["mbar2_size"] = self.__bar2_size

        opt_list = []
        opt_list.append("-device vmd")
        for k, v in args.items():
            opt_list.append("{}={}".format(k, v))

        self.add_option(",".join(opt_list))
