'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIIMC(CElement):
    '''
    PciIMC provides the function related with DIMM Device.
    Check its parameters and generate argument string.
    '''

    def __init__(self, imc_info):
        super(CPCIIMC, self).__init__()
        self.__imc_info = imc_info
        self.bus = None
        self.id = None
        self.device = "imc_m2mem"
        self.pcie_topo = None

    def precheck(self):
        if self.__imc_info.get("bus") is None:
            raise ArgsNotCorrect("imc bus is mandatory!")

        if self.__imc_info.get("id",) is None:
            raise ArgsNotCorrect("imc id is mandatory!")

        addr = self.__imc_info.get("addr",)
        if ((addr) != "08.0") and ((addr) != "09.0"):
            raise ArgsNotCorrect("imc address must be 08.0 or 09.0")

    def init(self):
        self.id = self.__imc_info["id"]
        self.bus = self.__imc_info["bus"]
        self.addr = self.__imc_info.get("addr")
        self.imc_slot_topo = self.__imc_info.get("imc_slot_topo")
        self.imc_cpu_index = self.__imc_info.get("imc_cpu_index")

    def handle_parms(self):
        args = {}
        args["id"] = self.id
        args["bus"] = self.bus
        args["multifunction"] = "on"
        args["addr"] = self.addr
        args["imc_slot_topo"] = self.imc_slot_topo
        args["imc_cpu_index"] = self.imc_cpu_index

        opt_list = []
        opt_list.append("-device imc_m2mem")
        for k, v in args.items():
            opt_list.append("{}={}".format(k, v))

        self.add_option(",".join(opt_list))
