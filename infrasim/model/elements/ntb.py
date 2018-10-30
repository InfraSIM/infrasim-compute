'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CNTB(CElement):
    '''
    SkxNtb provides the function related with Intel Skylake NTB Device.
    Check its parameters and generate argument string.
    '''

    def __init__(self, info):
        super(CNTB, self).__init__()
        self.__ntb_info = info
        self.__bar1_exp = None
        self.__bar2_exp = None
        self.__link_rx = None
        self.__link_tx = None
        self.id = None
        self.bus = None
        self.addr = None

    def precheck(self):
        if self.id is None:
            raise ArgsNotCorrect("NTB's id is mandatory!")

        if self.bus is None:
            raise ArgsNotCorrect("NTB's bus is mandatory!")

        if (self.__bar1_exp < 12 or self.__bar1_exp > 47):
            raise ArgsNotCorrect("exponent of bar1 size must in range [12,47].")

        if (self.__bar2_exp < 12 or self.__bar2_exp > 47):
            raise ArgsNotCorrect("exponent of bar2 size must in range [12,47].")

        if self.__link_rx is None:
            raise ArgsNotCorrect("peer device link_rx is mandatory.")

        if self.__link_tx is None:
            raise ArgsNotCorrect("local device is mandatory.")

    def init(self):
        self.id = self.__ntb_info["id"]
        self.bus = self.__ntb_info.get("bus", "pcie.0")
        self.addr = self.__ntb_info.get("addr", "0.0")
        self.__bar1_exp = self.__ntb_info.get("bar1_exp", 0)
        self.__bar2_exp = self.__ntb_info.get("bar2_exp", 0)
        self.__link_tx = self.__ntb_info.get("peer_rx")
        self.__link_rx = self.__ntb_info.get("local")

    def handle_parms(self):
        args = {}
        args["id"] = self.id
        args["bus"] = self.bus
        args["addr"] = self.addr
        args["region1size"] = self.__bar1_exp
        args["region2size"] = self.__bar2_exp
        args["link_rx"] = self.__link_rx
        args["link_tx"] = self.__link_tx

        opt_list = []
        opt_list.append("-device skx_ntb")
        for k, v in args.items():
            opt_list.append("{}={}".format(k, v))

        self.add_option(",".join(opt_list))
