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
from pci_vmd import CPCIVMD
from infrasim import ArgsNotCorrect


class CPCIETopology(CElement):
    def __init__(self, pcie_topology):
        super(CPCIETopology, self).__init__()
        self.__pcie_topology = pcie_topology
        self.__pcie_option = None
        self.__fw_cfg_obj = None
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

    def set_fw_cfg_obj(self, fw_cfg_obj):
        self.__fw_cfg_obj = fw_cfg_obj

    def check_id(self):
        id_list = []
        for component in self.__component_list:
            id_list.append(component['id'])

        if len(id_list) != len(set(id_list)):
            raise ArgsNotCorrect("PCIE device id duplicated")

    def __is_vmd_owned(self, component, collection):

        if component.device == "vmd":
            return True
        if component.bus == "pcie.0":
            return False

        parent = filter(lambda el: el.id == component.bus, collection)

        if parent is None or len(parent) != 1:
            raise ArgsNotCorrect("parent bus is wrong")

        return self.__is_vmd_owned(parent[0], collection)

    def precheck(self):
        if self.__pcie_topology is None:
            raise ArgsNotCorrect("pci topology is required.")

    def init(self):
        self.logger.info("topology start ")
        self.__component_list.append({'bus': -1,
                                      'id': 'pcie.0',
                                      'option': ""})
        pcie_topo_obj_list = []

        for root_port in self.__pcie_topology['root_port']:
            root_port_obj = CPCIERootport(root_port)
            pcie_topo_obj_list.append(root_port_obj)

        for vmd_element in self.__pcie_topology.get('vmd', []):
            vmd_obj = CPCIVMD(vmd_element)
            pcie_topo_obj_list.append(vmd_obj)

        if 'switch' in self.__pcie_topology:
            switch = self.__pcie_topology['switch']

            for switch_element in switch:
                for upstream in switch_element.get('upstream', []):
                    upstream_obj = CPCIEUpstream(upstream)
                    pcie_topo_obj_list.append(upstream_obj)

                for downstream in switch_element.get('downstream', []):
                    downstream_obj = CPCIEDownstream(downstream)
                    pcie_topo_obj_list.append(downstream_obj)

        for pcie_obj in pcie_topo_obj_list:
            pcie_obj.precheck()
            pcie_obj.init()

            # do not fix bus number behind vmd.
            if self.__is_vmd_owned(pcie_obj, pcie_topo_obj_list):
                pcie_obj.pcie_topo = None

            if self.__fw_cfg_obj and pcie_obj.pcie_topo:
                self.__fw_cfg_obj.add_topo(pcie_obj.pcie_topo)
            pcie_obj.handle_parms()
            pick_info_dic = {}
            pick_info_dic["bus"] = pcie_obj.bus
            pick_info_dic["id"] = pcie_obj.id
            pick_info_dic["option"] = pcie_obj.get_option()
            self.__component_list.append(pick_info_dic)

        self.check_id()

        self.logger.info("topology end")

    def handle_parms(self):
        self.build_topo(self.__component_list[0])
        self.add_option(self.__pcie_option)
