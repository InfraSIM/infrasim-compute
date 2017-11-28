'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement


class SESDevice(CElement):
    def __init__(self, ses_info):
        super(SESDevice, self).__init__()
        self._ses_info = ses_info

        self.prefix = "scsi"

        self.__port_wwn = None
        self.__channel = None
        self.__scsi_id = None
        self.__serial = None
        self.__wwn = None
        self.__lun = None
        self.__vendor = None
        self.__product = None
        self.__serial = None
        self.__version = None
        self.__bus = 0
        self.__dae_type = None

    def set_bus(self, bus):
        self.__bus = bus

    def precheck(self):
        pass

    def init(self):
        self.__port_wwn = self._ses_info.get("port_wwn")
        self.__channel = self._ses_info.get("channel")
        self.__scsi_id = self._ses_info.get("scsi-id")
        self.__lun = self._ses_info.get("lun")

        self.__vendor = self._ses_info.get("vendor")
        self.__product = self._ses_info.get("product")
        self.__serial = self._ses_info.get("serial")
        self.__wwn = self._ses_info.get("wwn")
        self.__version = self._ses_info.get("version")
        self.__dae_type = self._ses_info.get("dae_type")

    def handle_parms(self):
        options = {}

        if self.__channel:
            options["channel"] = self.__channel

        if self.__scsi_id:
            options["scsi-id"] = self.__scsi_id

        if self.__lun:
            options["lun"] = self.__lun

        if self.__product:
            options["product"] = self.__product

        if self.__vendor:
            options["vendor"] = self.__vendor

        if self.__serial:
            options["serial"] = self.__serial

        if self.__version:
            options["version"] = self.__version

        if self.__wwn:
            options["wwn"] = self.__wwn

        if self.__dae_type:
            options["dae_type"] = self.__dae_type

        options["bus"] = "{}{}.{}".format(self.prefix, self.__bus, 0)

        options_list = []
        for k, v in options.items():
            options_list.append("{}={}".format(k, v))

        ses_device_arguments = ",".join(options_list)

        self.add_option(",".join(["-device ses", ses_device_arguments]))
