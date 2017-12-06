'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIEDownstream(CElement):
    def __init__(self, downstream_info):
        super(CPCIEDownstream, self).__init__()
        self.__downstream_info = downstream_info
        self.bus = None
        self.id = None
        self.__slot = None
        self.__addr = None
        self.__device = None
        self.__chassis = None
        self.__downstream_option = None
        self.pcie_topo = {}

    def set_bdf(self):
        if self.__addr and 'pri_bus' in self.__downstream_info:
            pri_bus = self.__downstream_info.get('pri_bus')
            device, func = self.__addr.split('.')
            self.pcie_topo['bdf'] = (int(pri_bus) << 8) + (int(device) << 3) + int(func)

    def set_sec_bus(self):
        if self.__downstream_info.get('sec_bus'):
            self.pcie_topo['sec_bus'] = self.__downstream_info.get('sec_bus')

    def precheck(self):
        if self.__downstream_info is None:
            raise ArgsNotCorrect("downstream device is required.")
        if not set(['id', 'bus', 'chassis', 'slot']).issubset(self.__downstream_info):
            raise ArgsNotCorrect("downstream \
                <id>/<bus>/<chassis>/<slot> are all required.")

    def init(self):
        self.__device = self.__downstream_info.get('device')
        self.__chassis = self.__downstream_info.get('chassis')
        self.__slot = self.__downstream_info.get('slot')
        self.__addr = self.__downstream_info.get('addr')
        self.bus = self.__downstream_info.get('bus')
        self.id = self.__downstream_info.get('id')

        if self.__downstream_info.get('addr'):
            self.__addr = self.__downstream_info.get('addr')
        # step 1: set bdf
        self.set_bdf()
        # step 2: set sec_bus only when bdf is set
        if self.pcie_topo:
            self.set_sec_bus()

    def handle_parms(self):
        self.__downstream_option = " -device {},id={},bus={},chassis={},slot={}".format(
                                                            self.__device,
                                                            self.id,
                                                            self.bus,
                                                            self.__chassis,
                                                            self.__slot)
        if self.__addr:
            self.__downstream_option = ','.join([self.__downstream_option, "addr={}".format(self.__addr)])
        self.add_option(self.__downstream_option)
