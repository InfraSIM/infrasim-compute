'''
*********************************************************
Copyright @ 2018 DELLEMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

from infrasim.model.core.element import CElement


class CSerial(CElement):
    def __init__(self, chardev, serial_info):
        super(CSerial, self).__init__()
        self.__chardev = chardev
        self.__serial_info = serial_info
        # 0 - SOL
        # 3 - guest agent
        self.__index = None

    def precheck(self):
        if self.__chardev is None:
            raise ValueError("Missing chardev for serial device.")

        if self.__index == 3 and (self.__chardev.get_id() != "guest-agent"):
            raise ValueError("index 3 is reserved for guest agent.")

    def init(self):
        # index 3 reserved for guest agent
        self.__index = self.__serial_info.get("index")

    def handle_parms(self):
        serial_option = "-device isa-serial,chardev={}".format(self.__chardev.get_id())

        if self.__index is not None:
            serial_option = ",".join([serial_option, "index={}".format(self.__index)])

        self.add_option(serial_option)
