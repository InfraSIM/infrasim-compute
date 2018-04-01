'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import math
from infrasim.model.elements.storage import CBaseStorageController
from infrasim.model.elements.drive_scsi import SCSIDrive


class MegaSASController(CBaseStorageController):
    def __init__(self, controller_info):
        super(MegaSASController, self).__init__()
        self.__use_jbod = None
        self.__sas_address = None
        self.__msi = None
        self.__msix = None
        self.__max_cmds = None
        self.__max_sge = None
        self._controller_info = controller_info

    def precheck(self):
        # call parent precheck()
        super(MegaSASController, self).precheck()

    def init(self):
        # Call parent init()
        super(MegaSASController, self).init()

        self.__sas_address = self._controller_info.get('sas_address')
        self.__max_cmds = self._controller_info.get('max_cmds')
        self.__max_sge = self._controller_info.get('max_sge')
        self.__use_jbod = self._controller_info.get('use_jbod')
        self.__msi = self._controller_info.get('msi')
        self.__msix = self._controller_info.get('msix')

        self._start_idx = self.controller_index
        idx = 0
        for drive_info in self._controller_info.get("drives", []):
            sd_obj = SCSIDrive(drive_info)
            sd_obj.owner = self
            sd_obj.index = idx
            sd_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            sd_obj.set_scsi_id(idx % self._max_drive_per_controller)
            self._drive_list.append(sd_obj)
            idx += 1

        for drive_obj in self._drive_list:
            drive_obj.init()

        # Update controller index
        self.controller_index += (idx / self._max_drive_per_controller)

    def handle_parms(self):
        super(MegaSASController, self).handle_parms()

        drive_nums = len(self._drive_list)
        cntrl_nums = int(math.ceil(float(drive_nums) / self._max_drive_per_controller)) or 1

        bus_nr_generator = None

        if self._ptm:
            bus_nr_generator = self._ptm.get_available_bus()

        for cntrl_index in range(0, cntrl_nums):
            self._attributes["id"] = "scsi{}".format(self._start_idx + cntrl_index)
            if self.__use_jbod:
                self._attributes["use_jbod"] = self.__use_jbod

            if self.__sas_address:
                self._attributes["sas_address"] = self.__sas_address

            if self.__msi:
                self._attributes["msi"] = self.__msi

            if self.__msix:
                self._attributes["msix"] = self.__msix

            if self.__max_cmds:
                self._attributes["max_cmds"] = self.__max_cmds

            if self.__max_sge:
                self._attributes["max_sge"] = self.__max_sge

            if bus_nr_generator:
                self._attributes["bus"] = "pci.{}".format(bus_nr_generator.next())
                self._attributes["addr"] = 0x1

            self.add_option("{}".format(self._build_one_controller(self._model, **self._attributes)), 0)
