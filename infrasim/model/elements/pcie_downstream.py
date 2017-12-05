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
        self.addr = None
        self.__device = None
        self.__chassis = None
        self.downstream_option = None

    def set_option(self):
        self.downstream_option = " -device {},id={},bus={},chassis={},slot={}".format(
                                                            self.__device,
                                                            self.id,
                                                            self.bus,
                                                            self.__chassis,
                                                            self.__slot)

    def precheck(self):
        if self.__downstream_info is None:
            self.logger.exception("[PCIEDownstream] \
                Downstream device is required.")
            raise ArgsNotCorrect("downstream device is required.")
        if not set(['id', 'bus', 'chassis', 'slot']).issubset(self.__downstream_info):
            self.logger.exception("[PCIEDownstream] \
                Downstream <id>/<bus>/<chassis>/<slot> are all required.")
            raise ArgsNotCorrect("downstream \
                <id>/<bus>/<chassis>/<slot> are all required.")

    def init(self):
        self.__device = self.__downstream_info.get('device')
        self.__chassis = self.__downstream_info.get('chassis')
        self.__slot = self.__downstream_info.get('slot')
        self.addr = self.__downstream_info.get('addr')
        self.bus = self.__downstream_info.get('bus')
        self.id = self.__downstream_info.get('id')
