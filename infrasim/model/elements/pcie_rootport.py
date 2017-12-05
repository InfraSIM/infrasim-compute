'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIERootport(CElement):
    def __init__(self, rootport_info):
        super(CPCIERootport, self).__init__()
        self.__rootport_info = rootport_info
        self.__device = None
        self.__chassis = None
        self.__slot = None
        self.__addr = None
        self.id = None
        self.bus = None
        self.rootport_option = None
        self.pci_topo = {}
    def set_bdf(self):
        if self.__addr and 'pri_bus' in self.__rootport_info:
            pri_bus = self.__rootport_info.get('pri_bus')
            device, func = self.__addr.split('.')
            self.pci_topo['bdf'] = (int(pri_bus) << 8) + (int(device) << 3) + int(func)

    def set_sec_bus(self):
        if self.__rootport_info.get('sec_bus'):
            self.pci_topo['sec_bus'] = self.__rootport_info.get('sec_bus')

    def set_option(self):
        self.rootport_option = " -device {},id={},bus={},chassis={},slot={}".format(
                                                           self.__device,
                                                           self.id,
                                                           self.bus,
                                                           self.__chassis,
                                                           self.__slot)
        if self.__addr:
            self.rootport_option = ','.join([self.rootport_option,
                                             'addr={} '.format(self.__addr)])


    def precheck(self):
        if not self.__rootport_info:
            self.logger.exception("[PCIERootport] Rootport device is required.")
            raise ArgsNotCorrect("Rootport device is required.")
        if not set(['id', 'bus', 'chassis', 'slot']).issubset(self.__rootport_info):
            self.logger.exception("[PCIERootport] Rootport <id>/<bus>/<chassis>/<slot> are all required.")
            raise ArgsNotCorrect("Rootport <id>/<bus>/<chassis>/<slot> are all required.")

    def init(self):
        self.logger.info("Root port start ")
        self.__device = self.__rootport_info.get('device')
        self.id = self.__rootport_info.get('id')
        self.bus = self.__rootport_info.get('bus')
        self.__chassis = self.__rootport_info.get('chassis')
        self.__slot = self.__rootport_info.get('slot')
        if self.__rootport_info.get('addr'):
            self.__addr = self.__rootport_info.get('addr')
        # step 1: set bdf
        self.set_bdf()
        # step 2: set sec_bus only when bdf is set
        if self.pci_topo:
            self.set_sec_bus()
        self.logger.info("Root port end ")
