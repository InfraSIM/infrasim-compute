#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
from . import env
from infrasim import config
from infrasim.yaml_loader import YAMLLoader

def get_node_info():
    """
    Get runtime node information
    """
    runtime_yml_path = os.path.join(config.infrasim_home,
                                    env.node_name, "etc", "infrasim.yml")
    with open(runtime_yml_path, 'r') as fp:
        node_info = YAMLLoader(fp).get_data()

    return node_info


def get_drive_topology():

    topo_embedded = {}
    topo_backplane = {}

    node_info = get_node_info()

    d = node_info["compute"]["storage_backend"][0]["drives"][0]
    topo_embedded[0] = d

    for controller_idx, controller in enumerate(node_info["compute"]["storage_backend"][1:]):
        scsi_drives = controller["drives"]
        # FIXME: index drive slots
        # curr_hdd_slot = 0
        # curr_ssd_slot = 12
        # for the_drive in scsi_drives:
        #     # HDD
        #     if the_drive.get("rotation", 7200) > 1:
        #         drive_slot = the_drive.get("slot_number", curr_hdd_slot)
        #         if drive_slot >= curr_hdd_slot:
        #             the_drive["slot_number"] = drive_slot
        #             curr_hdd_slot += 1
        #         else:
        #             env.logger_r.exception("Invalid HDD slot")
        #             raise Exception("Invalid HDD slot")
        #
        #     # SSD
        #     else:
        #         drive_slot = the_drive.get("slot_number", curr_ssd_slot)
        #         if drive_slot >= curr_ssd_slot:
        #             the_drive["slot_number"] = drive_slot
        #             curr_hdd_slot += 1
        #         else:
        #             env.logger_r.exception("Invalid SSD slot")
        #             raise Exception("Invalid SSD slot")

        # Map drives to certain controller index
        topo_backplane[controller_idx+1] = scsi_drives

    return topo_embedded, topo_backplane
