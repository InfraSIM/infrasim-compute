'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


class CPCIEUpstream(CElement):
    def __init__(self, upstream_info):
        super(CPCIEUpstream, self).__init__()
        self.__upstream_info = upstream_info
        self.bus = None
        self.id = None
        self.__device = None
        self.__upstream_option = None
        self.pcie_topo = None

    def precheck(self):
        if self.__upstream_info is None:
            raise ArgsNotCorrect("upstream device is required.")
        if not set(['id', 'bus']).issubset(self.__upstream_info):
            raise ArgsNotCorrect("upstream <id>/<bus> are all required.")

    def init(self):
        self.__device = self.__upstream_info.get('device')
        self.bus = self.__upstream_info.get('bus')
        self.id = self.__upstream_info.get('id')

    def handle_parms(self):
        self.__upstream_option = " -device {},id={},bus={} ".format(
                                                           self.__device,
                                                           self.id,
                                                           self.bus)
        self.add_option(self.__upstream_option)
