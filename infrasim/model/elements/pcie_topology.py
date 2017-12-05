'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement
from pcie_rootport import CPCIERootport
from pcie_upstream import CPCIEUpstream
from pcie_downstream import CPCIEDownstream
from infrasim.helper import fw_cfg_file_create
from infrasim import ArgsNotCorrect


class CPCIETopology(CElement):
    def __init__(self, pcie_topology):
        super(CPCIETopology, self).__init__()
        self.__pcie_topology = pcie_topology
        self.__pcie_option = None
        self.__workspace = None
        self.fw_cfg_file = None
        self.__component_list = []

    def set_own_option(self, option, position):
        if self.__pcie_option is None:
            self.__pcie_option = option
            return

        if position is True:
            self.__pcie_option = " ".join(["{}".format(self.__pcie_option),
                                         "{}".format(option)])
        else:
            self.__pcie_option = " ".join(["{}".format(option),
                                         "{}".format(self.__pcie_option)])

    def build_topo(self, component):
        list_tmp = []
        for component_tmp in self.__component_list:
            if component_tmp["bus"] == component["id"]:
                list_tmp.append(component_tmp)

        if len(list_tmp):
            for component_tmp in list_tmp:
                self.build_topo(component_tmp)

        self.set_own_option(component["option"], False)
        return

    def set_workspace(self, ws):
        self.__workspace = ws

    def get_workspace(self):
        return self.__workspace

    def precheck(self):
        if self.__pcie_topology is None:
            self.logger.exception("[PCIETopology] PCIE topology is required.")
            raise ArgsNotCorrect("pci topology is required.")

    def init(self):
        self.logger.info("topology start ")
        self.__component_list.append({'bus': -1,
                                      'id': 'pcie.0',
                                      'option': ""})
        pci_topo_list = []
        for root_port in self.__pcie_topology['root_port']:
            root_port_obj = CPCIERootport(root_port)
            root_port_obj.precheck()
            root_port_obj.init()
            root_port_obj.set_option()
            pick_info_dic = {}
            pick_info_dic["bus"] = root_port_obj.bus
            pick_info_dic["id"] = root_port_obj.id
            pick_info_dic["option"] = root_port_obj.rootport_option
            self.__component_list.append(pick_info_dic)
            if root_port_obj.pci_topo:
                pci_topo_list.append(root_port_obj.pci_topo)
        self.fw_cfg_file = fw_cfg_file_create(pci_topo_list,
                                              self.get_workspace())

        switch = self.__pcie_topology['switch']

        for switch_element in switch:
            for upstream in switch_element.get('upstream', []):
                upstream_obj = CPCIEUpstream(upstream)
                upstream_obj.precheck()
                upstream_obj.init()
                upstream_obj.set_option()
                pick_info_dic = {}
                pick_info_dic["bus"] = upstream_obj.bus
                pick_info_dic["id"] = upstream_obj.id
                pick_info_dic["option"] = upstream_obj.upstream_option
                self.__component_list.append(pick_info_dic)

            for downstream in switch_element.get('downstream', []):
                downstream_obj = CPCIEDownstream(downstream)
                downstream_obj.precheck()
                downstream_obj.init()
                downstream_obj.set_option()
                pick_info_dic = {}
                pick_info_dic["bus"] = downstream_obj.bus
                pick_info_dic["id"] = downstream_obj.id
                pick_info_dic["option"] = downstream_obj.downstream_option
                self.__component_list.append(pick_info_dic)
        self.logger.info("topology end")

    def handle_parms(self):
        self.build_topo(self.__component_list[0])
        self.add_option(self.__pcie_option)
