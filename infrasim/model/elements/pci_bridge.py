'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim import ArgsNotCorrect
from infrasim.model.core.element import CElement


class CPCIBridge(CElement):
    def __init__(self, bridge_info):
        super(CPCIBridge, self).__init__()
        self.__bridge_info = bridge_info
        self.__children_bridge_list = None
        self.__current_bridge_device = None
        self.__addr = None
        self.__bus = None
        self.__parent = None
        self.__can_use_bus = False
        self.__chassis_nr = None
        self.__msi = None
        self.__multifunction = None

    def set_bus(self, bus_nr):
        self.__bus = bus_nr

    def get_bus(self):
        return self.__bus

    def get_bus_list(self):
        bus_list = []
        for br_obj in self.__children_bridge_list:
            if br_obj.__can_use_bus:
                bus_list.append(br_obj.get_bus())
        return bus_list

    def set_parent(self, parent):
        self.__parent = parent

    def get_parent(self):
        return self.__parent

    def precheck(self):
        if self.__current_bridge_device is None:
            raise ArgsNotCorrect("[PCIBridge] bridge device is required.")

    def init(self):
        self.__current_bridge_device = self.__bridge_info.get('device')
        self.__addr = self.__bridge_info.get('addr')
        self.__chassis_nr = self.__bridge_info.get('chassis_nr')
        self.__msi = self.__bridge_info.get('msi')
        self.__multifunction = self.__bridge_info.get('multifunction')

        if 'downstream_bridge' not in self.__bridge_info:
            return

        self.__children_bridge_list = []
        current_bus_nr = self.__bus + 1
        for child_br in self.__bridge_info['downstream_bridge']:
            child_obj = CPCIBridge(child_br)
            child_obj.logger = self.logger
            child_obj.set_bus(current_bus_nr)
            child_obj.__can_use_bus = True
            child_obj.set_parent("pci.{}".format(self.__bus))
            self.__children_bridge_list.append(child_obj)
            current_bus_nr += 1

        for child_obj in self.__children_bridge_list:
            child_obj.init()

    def handle_parms(self):
        bridge_option = "-device {},bus={},id=pci.{}".format(
                            self.__current_bridge_device,
                            self.__parent,
                            self.__bus
                            )
        if self.__addr:
            bridge_option = ",".join([bridge_option, "addr={}".format(self.__addr)])

        if self.__chassis_nr:
            bridge_option = ",".join([bridge_option, "chassis_nr={}".format(self.__chassis_nr)])

        if self.__msi:
            bridge_option = ",".join([bridge_option, "msi={}".format(self.__msi)])

        if self.__multifunction:
            bridge_option = ",".join([bridge_option, "multifunction={}".format(self.__multifunction)])

        self.add_option(bridge_option)

        if self.__children_bridge_list is None:
            return

        for child_obj in self.__children_bridge_list:
            child_obj.handle_parms()

        for child_obj in self.__children_bridge_list:
            self.add_option(child_obj.get_option())
