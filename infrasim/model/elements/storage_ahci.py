'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import math
from infrasim.model.elements.storage import CBaseStorageController
from infrasim.model.elements.drive_ide import IDEDrive


class AHCIController(CBaseStorageController):
    def __init__(self, controller_info, cdrom_connected=False):
        super(AHCIController, self).__init__()
        self._controller_info = controller_info
        self.__unit = 0
        self.__is_cdrom_connected = cdrom_connected

    def precheck(self):
        # call parent precheck()
        super(AHCIController, self).precheck()

    def init(self):
        super(AHCIController, self).init()

        self._start_idx = self.controller_index

        # reserv 0 for cdrom
        idx = 1 if (self.__is_cdrom_connected is True) else 0

        for drive_info in self._controller_info.get("drives", []):
            ide_obj = IDEDrive(drive_info)
            ide_obj.logger = self.logger
            ide_obj.index = idx
            ide_obj.owner = self
            ide_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            ide_obj.set_scsi_id(idx % self._max_drive_per_controller)
            self._drive_list.append(ide_obj)
            idx += 1

        for drive_obj in self._drive_list:
            drive_obj.init()

        # Update controller index
        self.controller_index += (idx / self._max_drive_per_controller)

    def handle_parms(self):
        super(AHCIController, self).handle_parms()

        drive_nums = len(self._drive_list)
        drive_nums = drive_nums if (self.__is_cdrom_connected is False) else drive_nums + 1
        cntrl_nums = int(math.ceil(float(drive_nums) / self._max_drive_per_controller)) or 1
        for cntrl_index in range(0, cntrl_nums):
            self._attributes["id"] = "sata{}".format(self._start_idx + cntrl_index)
            self.add_option("{}".format(self._build_one_controller(self._model, **self._attributes)), 0)
