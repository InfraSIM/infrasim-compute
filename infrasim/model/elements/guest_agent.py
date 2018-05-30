'''
*********************************************************
Copyright @ 2018 DELLEMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
from infrasim.model.core.element import CElement
from infrasim.model.elements.chardev import CCharDev
from infrasim.model.elements.serial import CSerial


class GuestAgent(CElement):
    def __init__(self, workspace):
        super(GuestAgent, self).__init__()
        self.__chardev = None
        self.__workspace = workspace
        self.__serial = None

    def precheck(self):
        if self.__chardev:
            self.__chardev.precheck()

        if self.__serial:
            self.__serial.precheck()

    def init(self):
        self.__chardev = CCharDev({
            "backend": "socket",
            "path": os.path.join(self.__workspace, "guest.agt"),
            "server": "on",
            "wait": False
        })
        self.__chardev.set_id("guest-agent")
        self.__chardev.init()

        self.__serial = CSerial(self.__chardev,
                                {"index": 3})
        self.__serial.init()

    def handle_parms(self):
        self.__chardev.handle_parms()
        self.__serial.handle_parms()
        self.add_option(self.__chardev.get_option())
        self.add_option(self.__serial.get_option())
