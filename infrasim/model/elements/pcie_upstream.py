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
        self.upstream_option = None

    def set_option(self):
        self.upstream_option = " -device {},id={},bus={} ".format(
                                                           self.__device,
                                                           self.id,
                                                           self.bus)

    def precheck(self):
        if self.__upstream_info is None:
            self.logger.exception("[PCIEUpstream] Upstream device is required.")
            raise ArgsNotCorrect("upstream device is required.")
        if not set(['id','bus']).issubset(self.__upstream_info):
            self.logger.exception("[PCIEUpstream] Upstream <id>/<bus> are all required.")
            raise ArgsNotCorrect("upstream <id>/<bus> are all required.")


    def init(self):
        self.__device = self.__upstream_info.get('device')
        self.bus = self.__upstream_info.get('bus')
        self.id = self.__upstream_info.get('id')
