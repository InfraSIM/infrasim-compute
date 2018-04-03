'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
import json
from infrasim import ArgsNotCorrect
from infrasim import run_command
from infrasim import helper
from infrasim.model.core.element import CElement


class CNetwork(CElement):
    def __init__(self, network_info):
        super(CNetwork, self).__init__()
        self.__network = network_info
        self.__network_list = []
        self.__network_mode = None
        self.__bridge_name = None
        self.__nic_name = None
        self.__mac_address = None
        self.__index = 0
        self.__bus = None
        self.__addr = None
        self.__multifunction = None

    def set_index(self, index):
        self.__index = index

    def precheck(self):
        # Check if parameters are valid
        # bridge exists?
        if self.__network_mode == "bridge":
            if self.__bridge_name is None:
                if "br0" not in helper.get_all_interfaces():
                    raise ArgsNotCorrect("[CNetwork] ERROR: network_name(br0) does not exist")
            else:
                if self.__bridge_name not in helper.get_all_interfaces():
                    raise ArgsNotCorrect("[CNetwork] ERROR: network_name({}) does not exist".
                                         format(self.__bridge_name))
            if "mac" not in self.__network:
                raise ArgsNotCorrect("[CNetwork] ERROR: mac address is not specified for "
                                     "target network:\n{}".
                                     format(json.dumps(self.__network, indent=4)))
            else:
                list_addr = self.__mac_address.split(":")
                if len(list_addr) != 6:
                    raise ArgsNotCorrect("[CNetwork] ERROR: mac address invalid: {}".
                                         format(self.__mac_address))
                for each_addr in list_addr:
                    try:
                        int(each_addr, 16)
                    except Exception:
                        raise ArgsNotCorrect("[CNetwork] ERROR: mac address invalid: {}".
                                             format(self.__mac_address))

    def init(self):
        self.__network_mode = self.__network.get('network_mode', "nat")
        self.__bridge_name = self.__network.get('network_name')
        self.__nic_name = self.__network.get('device')
        self.__mac_address = self.__network.get('mac')
        self.__bus = self.__network.get('bus')
        self.__addr = self.__network.get('addr')
        self.__multifunction = self.__network.get('multifunction')

    def handle_parms(self):
        if self.__network_mode == "bridge":
            if self.__bridge_name is None:
                self.__bridge_name = "br0"

            qemu_sys_prefix = os.path.dirname(
                run_command("which qemu-system-x86_64")[1]
            ).replace("bin", "")
            bridge_helper = os.path.join(qemu_sys_prefix,
                                         "libexec",
                                         "qemu-bridge-helper")
            netdev_option = ",".join(['bridge', 'id=netdev{}'.format(self.__index),
                                      'br={}'.format(self.__bridge_name),
                                      'helper={}'.format(bridge_helper)])

        elif self.__network_mode == "nat":
            netdev_option = ",".join(["user", "id=netdev{}".format(self.__index)])
        else:
            raise ArgsNotCorrect("[CNetwork] ERROR: Network mode '{}'' is not supported now.".
                                 format(self.__network_mode))

        nic_option = ",".join(["{}".format(self.__nic_name),
                               "netdev=netdev{}".format(self.__index),
                               "mac={}".format(self.__mac_address)])
        if self.__bus:
            nic_option = ",".join(["{}".format(nic_option),
                                   "bus={}".format(self.__bus)])
        if self.__addr:
            nic_option = ",".join(["{}".format(nic_option),
                                   "addr={}".format(self.__addr)])
        if self.__multifunction:
            nic_option = ",".join(["{}".format(nic_option),
                                   "multifunction={}".format(self.__multifunction)])

        network_option = " ".join(["-netdev {}".format(netdev_option),
                                   "-device {}".format(nic_option)])
        self.add_option(network_option)
