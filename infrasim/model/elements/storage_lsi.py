'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import math
from infrasim import helper
from infrasim.model.elements.storage import CBaseStorageController
from infrasim.model.elements.drive_scsi import SCSIDrive
from infrasim.model.elements.ses import SESDevice
from infrasim.model.elements.storage_diskarray import DiskArrayController
import os


class LSISASController(CBaseStorageController):
    def __init__(self, controller_info):
        super(LSISASController, self).__init__()
        self._controller_info = controller_info
        self._iothread_id = None
        self.__use_msix = None
        self.__dae_file = None
        self.__sas_address = None

    def precheck(self):
        # call parent precheck()
        super(LSISASController, self).precheck()

    def init(self):
        super(LSISASController, self).init()

        self._iothread_id = self._controller_info.get("iothread")
        self.__use_msix = self._controller_info.get('use_msix')
        self.__sas_address = self._controller_info.get('sas_address')

        self._start_idx = self.controller_index
        idx = 0
        for drive_info in self._controller_info.get("drives", []):
            sd_obj = SCSIDrive(drive_info)
            sd_obj.logger = self.logger
            sd_obj.index = idx
            sd_obj.owner = self
            sd_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            sd_obj.set_scsi_id(idx % self._max_drive_per_controller)
            self._drive_list.append(sd_obj)
            idx += 1

        for ses_info in self._controller_info.get("seses", []):
            ses_obj = SESDevice(ses_info)
            ses_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            self._ses_list.append(ses_obj)

        for drive_obj in self._drive_list:
            drive_obj.init()

        for ses_obj in self._ses_list:
            ses_obj.init()

        ws = helper.get_ws_folder(self)
        self.__dae_file = os.path.join(ws, "data", "diskarray{}.json".format(self.controller_index))

        # Update controller index, tell CBackendStorage what the controller index
        # should be for the next
        self.controller_index += (idx / self._max_drive_per_controller)

    def handle_parms(self):
        drv_args = []
        # handle drive options
        for drive_obj in self._drive_list:
            drive_obj.handle_parms()
            # export options to json file
            drv_args.append(drive_obj.get_option())

        self._drive_list = []

        super(LSISASController, self).handle_parms()

        drive_nums = len(self._drive_list)
        cntrl_nums = int(math.ceil(float(drive_nums) / self._max_drive_per_controller)) or 1
        for cntrl_index in range(0, cntrl_nums):
            self._attributes["id"] = "scsi{}".format(self._start_idx + cntrl_index)

            if self._iothread_id:
                self._attributes["iothread"] = self._iothread_id

            if self.__use_msix is not None:
                self._attributes["use_msix"] = self.__use_msix

            if self.__sas_address:
                self._attributes["sas_address"] = self.__sas_address

            if self.__dae_file is not None:
                self._attributes["dae_file"] = self.__dae_file

            self.add_option("{}".format(self._build_one_controller(self._model, **self._attributes)), 0)

        DiskArrayController.export_json_data(self.__dae_file, drv_args, self._controller_info)
