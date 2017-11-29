'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.elements.drive import CBaseDrive


class IDEDrive(CBaseDrive):
    def __init__(self, drive_info):
        super(IDEDrive, self).__init__()
        self._name = "ide-hd"
        self.prefix = "sata"
        self._drive_info = drive_info
        self.__model = None
        self.__unit = None
        self.__bus_address = None

        # identify a drive on which controller
        # self.__bus is controller index
        self.__bus = 0
        self._scsi_id = 0
        self._channel = 0
        self._lun = 0

    # controller index
    def set_bus(self, bus):
        self.__bus = bus

    def get_uniq_name(self):
        return "{}-{}".format(self.__bus, self.index)

    def set_scsi_id(self, scsi_id):
        self._scsi_id = scsi_id

    def set_unit(self, unit):
        self.__unit = unit

    def init(self):
        super(IDEDrive, self).init()

        self.__model = self._drive_info.get("model")

    def handle_parms(self):
        super(IDEDrive, self).handle_parms()

        drive_id = "{}{}-{}-{}-{}".format(self.prefix,
                                          self.__bus,
                                          self._channel,
                                          self._scsi_id,
                                          self._lun)

        # Host option
        self._host_opt["if"] = "none"
        self._host_opt["id"] = drive_id

        self.add_option(self.build_host_option(**self._host_opt))

        # Device option

        # For ATA controller, one bus holds only one target,
        # AHCI could support at most 6 target devices each controller
        if self.__bus_address is None:
            b = self._scsi_id
            self.__bus_address = "{}{}.{}".format(self.prefix, self.__bus, b)

        self._dev_attrs["bus"] = self.__bus_address

        self._dev_attrs["drive"] = drive_id

        self._dev_attrs["id"] = "dev-{}".format(self._dev_attrs["drive"])

        if self.__model:
            self._dev_attrs["model"] = self.__model

        if self.__unit is not None:
            self._dev_attrs["unit"] = self.__unit

        self.add_option(self.build_device_option(self._name, **self._dev_attrs))
