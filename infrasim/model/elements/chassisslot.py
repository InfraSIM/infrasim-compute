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

    def add_slot_map(self, chassis_slot, dev_attrs):
        if not isinstance(chassis_slot, int) or chassis_slot < 0:
            return

        if chassis_slot not in range(0, 25):
            raise ArgsNotCorrect("[BackendStorage] Unsupported chassis slot: {}".
                                 format(chassis_slot))
        key = "slot_{}".format(chassis_slot)
        if self.__nvme_map_dict.has_key(key):
            raise ArgsNotCorrect("[BackendStorage] Chassis slot: {} has been used".
                                 format(chassis_slot))
        nvme_map_dict = dev_attrs
        nvme_map_dict["model_number"] = dev_attrs.get("model_number", "").replace("\"", "")
        nvme_map_dict["drive"] = dev_attrs.get("id", "").replace("dev-", "")
        nvme_map_dict["power_status"] = "on"
        self.__nvme_map_dict[key] = nvme_map_dict
        self.logger.info("Add slot: {} nvme_map_dict: {}".
                         format(chassis_slot, nvme_map_dict))

    def precheck(self):
        pass

    def init(self):
        pass

    def handle_parms(self):
        # gen oem data
        self.logger.info("Fill OEM json file")
        filename = os.path.join(self.__workspace, "data/oem_data.json")
        if not self.__nvme_map_dict or not os.path.exists(filename):
            self.logger.info("oem_data.json not exist or nvme_map_dict is empty")
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
