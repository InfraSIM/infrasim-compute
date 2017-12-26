'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIEPort(CElement):
    def __init__(self, port_info):
        super(CPCIEPort, self).__init__()
        self.__port_info = port_info
        self.__device = None
        self.__chassis = None
        self.__slot = None
        self.__addr = None
        self.__multifunction = None
        self.__port_option = None
        self.id = None
        self.bus = None
        self.pcie_topo = {}

    def set_bdf(self):
        if self.__addr and 'pri_bus' in self.__port_info:
            pri_bus = self.__port_info.get('pri_bus')
            device, func = self.__addr.split('.')
            self.pcie_topo['bdf'] = (int(pri_bus) << 8) + (int(device, 16) << 3) + int(func)

    def set_sec_bus(self):
        if self.__port_info.get('sec_bus'):
            self.pcie_topo['sec_bus'] = self.__port_info.get('sec_bus')

    def precheck(self):
        if not self.__port_info:
            raise ArgsNotCorrect("port device is required.")
        if not set(['id', 'bus', 'chassis', 'slot']).issubset(self.__port_info):
            raise ArgsNotCorrect("port \
                 <id>/<bus>/<chassis>/<slot> are all required.")

    def init(self):
        self.logger.info("port start ")
        self.__device = self.__port_info.get('device')
        self.id = self.__port_info.get('id')
        self.bus = self.__port_info.get('bus')
        self.__chassis = self.__port_info.get('chassis')
        self.__slot = self.__port_info.get('slot')
        self.__addr = self.__port_info.get('addr')
        self.__multifunction = self.__port_info.get('multifunction')
        # step 1: set bdf
        self.set_bdf()
        # step 2: set sec_bus only when bdf is set
        if self.pcie_topo:
            self.set_sec_bus()

        self.logger.info("port end ")

    def handle_parms(self):
        self.__port_option = " -device {},id={},bus={},chassis={},slot={}".format(
                                                           self.__device,
                                                           self.id,
                                                           self.bus,
                                                           self.__chassis,
                                                           self.__slot)
        if self.__addr:
            self.__port_option = ','.join([self.__port_option,
                                             'addr={}'.format(self.__addr)])
        if self.__multifunction:
            self.__port_option = ','.join([self.__port_option,
                                             'multifunction={} '.format(self.__multifunction)])
        self.add_option(self.__port_option)
