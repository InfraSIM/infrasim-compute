'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from infrasim.model.elements.pci_bridge import CPCIBridge


class CPCITopologyManager(CElement):
    def __init__(self, pci_topology_info):
        super(CPCITopologyManager, self).__init__()
        self.__pci_topology_info = pci_topology_info
        self.__bridge_list = []
        self.__available_bus_list = []

    def get_available_bus(self):
        for bus_nr in self.__available_bus_list:
            yield bus_nr

    def precheck(self):
        pass

    def init(self):
        current_bus_nr = 1
        for bri in self.__pci_topology_info:
            bridge_obj = CPCIBridge(bri)
            bridge_obj.logger = self.logger
            bridge_obj.set_bus(current_bus_nr)
            bridge_obj.set_parent("pcie.0")
            self.__bridge_list.append(bridge_obj)
            current_bus_nr += 1

        for br_obj in self.__bridge_list:
            br_obj.init()

        for br_obj in self.__bridge_list:
            self.__available_bus_list.extend(br_obj.get_bus_list())

    def handle_parms(self):
        for br_obj in self.__bridge_list:
            br_obj.handle_parms()

        for br_obj in self.__bridge_list:
            self.add_option(br_obj.get_option())
