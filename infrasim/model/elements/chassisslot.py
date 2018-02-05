'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import codecs
import json
from infrasim import ArgsNotCorrect
from infrasim.model.core.element import CElement


class CChassisSlot(CElement):
    def __init__(self, backend_storage_info, workspace):
        super(CChassisSlot, self).__init__()
        self.__backend_storage_info = backend_storage_info
        self.__workspace = workspace
        self.__nvme_map_dict = {}

    def add_slot_map(self, chassis_slot, device_id, drive_id, serial, bus, cmb_size_mb):
        if not chassis_slot:
            return

        if chassis_slot not in range(0, 25):
            raise ArgsNotCorrect("[BackendStorage] Unsupported chassis slot: {}".
                                 format(chassis_slot))
        key = "slot_{}".format(chassis_slot)
        if self.__nvme_map_dict.has_key(key):
            raise ArgsNotCorrect("[BackendStorage] Chassis slot: {} has been used".
                                 format(chassis_slot))
        nvme_map_dict = {}
        nvme_map_dict["device_id"] = device_id
        nvme_map_dict["drive_id"] = drive_id
        nvme_map_dict["serial"] = serial
        nvme_map_dict["power_status"] = "on"
        nvme_map_dict["bus"] = bus
        nvme_map_dict["cmb_size_mb"] = cmb_size_mb
        self.__nvme_map_dict[key] = nvme_map_dict
        self.logger.info("Add slot: {} device id: {} \
                         drive id: {} serial: {} \
                         bus: {} cmd_size_mb: {}".
                         format(chassis_slot, device_id, drive_id,
                                serial, bus, cmb_size_mb))

    def precheck(self):
        pass

    def init(self):
        pass

    def handle_parms(self):
        # gen oem data
        self.logger.info("Fill OEM json file")
        filename = os.path.join(self.__workspace, "data/oem_data.json")
        if not self.__nvme_map_dict or not os.path.exists(filename):
            self.logger.info("Fill OEM json file: Do nothing!")
            return

        with codecs.open(filename, 'r', 'utf-8') as f:
            oem_dict = json.load(f)

        nvme_dict = oem_dict.get('nvme')
        for slot_id in self.__nvme_map_dict.keys():
            if nvme_dict.has_key(slot_id):
                nvme_dict[slot_id].update(self.__nvme_map_dict[slot_id])
            else:
                nvme_dict[slot_id] = self.__nvme_map_dict[slot_id]
        oem_dict['nvme'] = nvme_dict
        with open(filename, 'w') as f:
            json.dump(oem_dict, f, indent=4)
        self.logger.info("Fill OEM json file: Done!")
