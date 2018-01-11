'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from infrasim.helper import fw_cfg_file_create


class CPCIEFwcfg(CElement):
    def __init__(self):
        super(CPCIEFwcfg, self).__init__()
        self.__topo_list = []
        self.__fw_cfg_file = None
        self.__workspace = None

    def precheck(self):
        pass

    def set_workspace(self, ws):
        self.__workspace = ws

    def get_workspace(self):
        return self.__workspace

    def add_topo(self, topo_list):
        self.__topo_list.append(topo_list)

    def init(self):
        self.logger.info("PCIEFwcfg start ")

        if self.__topo_list:
            self.__fw_cfg_file = fw_cfg_file_create(self.__topo_list, self.get_workspace())

        self.logger.info("PCIEFwcfg end ")

    def handle_parms(self):
        if self.__fw_cfg_file:
            self.add_option("-fw_cfg name=opt/bios.pci_topo,file={}".format(self.__fw_cfg_file))
