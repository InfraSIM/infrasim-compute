'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
from infrasim import config
from infrasim.model.core.element import CElement
from infrasim.model.elements.chardev import CCharDev
from infrasim.model.elements.serial import CSerial


class QTrace(CElement):
    def __init__(self, trace_settings, workspace):
        super(QTrace, self).__init__()
        self.__seabios_out = trace_settings.get("seabios")
        self.__guest_out = trace_settings.get("guest")

        self.__chardev_for_so = None

        self.__chardev_for_go = None
        self.__serial_for_go = None
        self.__node_name = workspace.split('/')[-1]

    def precheck(self):
        pass

    def init(self):
        if self.__seabios_out == "on":
            self.__chardev_for_so = CCharDev({
                "backend": "file",
                "path": os.path.join(config.infrasim_log_dir, self.__node_name, "seabios.log"),
            })
            self.__chardev_for_so.set_id("seabios")
            self.__chardev_for_so.init()

        if self.__guest_out == "on":
            self.__chardev_for_go = CCharDev({
                "backend": "file",
                "path": os.path.join(config.infrasim_log_dir, self.__node_name, "guest.log")
            })

            self.__chardev_for_go.set_id("guest")
            self.__chardev_for_go.init()

            self.__serial_for_go = CSerial(self.__chardev_for_go, {"index": "0"})
            self.__serial_for_go.init()

    def handle_parms(self):
        if self.__chardev_for_so:
            self.__chardev_for_so.handle_parms()
            self.add_option("{} -device isa-debugcon,iobase=0x402,chardev=seabios".format(
                self.__chardev_for_so.get_option()))

        if self.__chardev_for_go and self.__serial_for_go:
            self.__chardev_for_go.handle_parms()
            self.__serial_for_go.handle_parms()
            self.add_option(self.__chardev_for_go.get_option())
            self.add_option(self.__serial_for_go.get_option())
