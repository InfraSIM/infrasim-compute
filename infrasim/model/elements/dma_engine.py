'''
*********************************************************
Copyright @ 2018 Dell EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CDMAEngine(CElement):
    '''
    DmaEngine provides the function related with IOAT DMA Device.
    Check its parameters and generate argument string.
    '''

    def __init__(self, info):
        super(CDMAEngine, self).__init__()
        self.__dma_info = info
        self.__count = 0
        self.id = None
        self.bus = None
        self.addr = None

    def precheck(self):
        if self.id is None:
            raise ArgsNotCorrect("NTB's id is mandatory!")

        if self.bus is None:
            raise ArgsNotCorrect("NTB's bus is mandatory!")

    def init(self):
        self.id = self.__dma_info["id"]
        self.bus = self.__dma_info.get("bus", "pcie.0")
        self.addr = self.__dma_info.get("addr", "0.0")
        self.__count = self.__dma_info.get("count", 8)

    def handle_parms(self):
        dev_nr = self.addr.split(".")[0]
        for idx in range(0, self.__count):
            args = {}
            args["id"] = "{}_{}".format(self.id, idx)
            args["bus"] = self.bus
            args["addr"] = "{}.{}".format(dev_nr, idx)
            args["multifunction"] = 'on'

            opt_list = []
            opt_list.append("-device ioat_dma")
            for k, v in args.items():
                opt_list.append("{}={}".format(k, v))

            self.add_option(",".join(opt_list))
