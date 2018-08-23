'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
from infrasim import ArgsNotCorrect
from infrasim import helper
from infrasim.model.core.element import CElement
from infrasim.model.elements.network import CNetwork
from infrasim.model.elements.storage_mega import MegaSASController
from infrasim.model.elements.storage_lsi import LSISASController
from infrasim.model.elements.storage_pmc import PMCSASController
from infrasim.model.elements.drive_nvme import NVMeController
from infrasim.model.elements.storage_ahci import AHCIController
from infrasim.model.elements.chassisslot import CChassisSlot
from infrasim.model.elements.storage_diskarray import DiskArrayController


class CBackendNetwork(CElement):

    def __init__(self, network_info_list):
        super(CBackendNetwork, self).__init__()
        self.__backend_network_list = network_info_list

        self.__network_list = []

    def precheck(self):
        for network_obj in self.__network_list:
            network_obj.precheck()

    def init(self):
        index = 0
        for network in self.__backend_network_list:
            network_obj = CNetwork(network)
            network_obj.logger = self.logger
            network_obj.set_index(index)
            self.__network_list.append(network_obj)
            index += 1

        for network_obj in self.__network_list:
            network_obj.init()

    def handle_parms(self):
        for network_obj in self.__network_list:
            network_obj.handle_parms()

        for network_obj in self.__network_list:
            self.add_option(network_obj.get_option())


class CBackendStorage(CElement):

    def __init__(self, backend_storage_info, cdrom_connected=False):
        super(CBackendStorage, self).__init__()
        self.__backend_storage_info = backend_storage_info
        self.__controller_list = []
        self.__pci_topology_manager = None
        self.__is_cdrom_connected = cdrom_connected

        # Global controller index managed by CBackendStorage
        self.__sata_controller_index = 0
        self.__scsi_controller_index = 0
        self.__nvme_controller_index = 0

    def set_pci_topology_mgr(self, ptm):
        self.__pci_topology_manager = ptm

    def precheck(self):
        for controller_obj in self.__controller_list:
            controller_obj.precheck()

    def __create_controller(self, controller_info):
        controller_obj = None
        model = controller_info.get("type", "ahci")
        if model.startswith("megasas"):
            controller_obj = MegaSASController(controller_info)
        elif model.startswith("lsi"):
            controller_obj = LSISASController(controller_info)
        elif model.startswith("pmc"):
            controller_obj = PMCSASController(controller_info)
        elif "nvme" in model:
            controller_obj = NVMeController(controller_info)
        elif "ahci" in model:
            controller_obj = AHCIController(controller_info, self.__is_cdrom_connected)
        else:
            raise ArgsNotCorrect("[BackendStorage] Unsupported controller type: {}".
                                 format(model))

        controller_obj.logger = self.logger
        # set owner
        controller_obj.owner = self
        return controller_obj

    def __init_diskarray(self):
        ws = os.path.join(helper.get_ws_folder(self), "data")
        diskarray = DiskArrayController(ws)
        diskarray.add_storage_backend(self.__backend_storage_info)
        dae_topo = diskarray.get_topo()
        if dae_topo is not None:
            filename = os.path.join(ws, "sas_topo.bin")
            with open(filename, "w") as f:
                f.write(dae_topo)
            diskarray.set_topo_file(self.__backend_storage_info, filename)
            diskarray.export_drv_data()
        diskarray.merge_drv_data(self.__backend_storage_info)
        self.__backend_storage_info = filter(lambda x: x["type"] != "disk_array", self.__backend_storage_info)

    def init(self):
        self.__init_diskarray()
        for controller in self.__backend_storage_info:
            controller_obj = self.__create_controller(controller)
            if self.__pci_topology_manager:
                controller_obj.set_pci_topology_mgr(self.__pci_topology_manager)
            self.__controller_list.append(controller_obj)

        for controller_obj in self.__controller_list:
            if isinstance(controller_obj, AHCIController):
                controller_obj.controller_index = self.__sata_controller_index
            elif isinstance(controller_obj, NVMeController):
                controller_obj.controller_index = self.__nvme_controller_index
            else:
                controller_obj.controller_index = self.__scsi_controller_index
            controller_obj.init()

            if isinstance(controller_obj, AHCIController):
                self.__sata_controller_index = controller_obj.controller_index + 1
            elif isinstance(controller_obj, NVMeController):
                self.__nvme_controller_index = controller_obj.controller_index + 1
            else:
                self.__scsi_controller_index = controller_obj.controller_index + 1

    def handle_parms(self):
        # store chassis slot map to controller
        chassis_slot = CChassisSlot(self.__backend_storage_info,
                                    helper.get_ws_folder(self))

        for controller_obj in self.__controller_list:
            controller_obj.handle_parms()
            if isinstance(controller_obj, NVMeController):
                chassis_slot.add_slot_map(controller_obj.chassis_slot, controller_obj.dev_attrs)
        chassis_slot.handle_parms()

        for controller_obj in self.__controller_list:
            self.add_option(controller_obj.get_option())
