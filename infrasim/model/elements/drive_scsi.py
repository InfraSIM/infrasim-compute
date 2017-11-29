'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.elements.drive import CBaseDrive


class SCSIDrive(CBaseDrive):
    def __init__(self, drive_info):
        super(SCSIDrive, self).__init__()
        self._name = "scsi-hd"
        self.prefix = "scsi"
        self._drive_info = drive_info

        self.__rotation = None
        self.__port_wwn = None
        self.__slot_number = None
        self.__product = None
        self.__vendor = None
        self.__port_index = None
        self.__atta_wwn = None
        self.__atta_phy_id = None
        self.__bus_address = None

        # identify a drive on which controller
        # self.__bus is controller index
        self.__bus = 0
        self._scsi_id = 0
        self._channel = 0
        self._lun = 0

    def precheck(self):
        super(SCSIDrive, self).precheck()

    # controller index
    def set_bus(self, bus):
        self.__bus = bus

    def get_uniq_name(self):
        return "{}-{}".format(self.__bus, self.index)

    def set_scsi_id(self, scsi_id):
        self._scsi_id = scsi_id

    def init(self):
        super(SCSIDrive, self).init()

        self.__port_index = self._drive_info.get('port_index')
        self.__port_wwn = self._drive_info.get('port_wwn')
        self._channel = self._drive_info.get('channel', self._channel)
        self._scsi_id = self._drive_info.get('scsi-id', self._scsi_id)
        self._lun = self._drive_info.get('lun', self._lun)
        self.__slot_number = self._drive_info.get('slot_number')
        self.__product = self._drive_info.get('product')
        self.__vendor = self._drive_info.get('vendor')
        self.__rotation = self._drive_info.get('rotation')
        self.__atta_wwn = self._drive_info.get('atta_wwn')
        self.__atta_phy_id = self._drive_info.get('atta_phy_id')

    def handle_parms(self):
        super(SCSIDrive, self).handle_parms()

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

        # For SCSI controller, one controller supports only one bus,
        # with at most 8 drives on this bus.
        if self.__bus_address is None:
            b = self._channel
            self.__bus_address = "{}{}.{}".format(self.prefix, self.__bus, b)

        self._dev_attrs["bus"] = self.__bus_address

        self._dev_attrs["drive"] = drive_id

        self._dev_attrs["id"] = "dev-{}".format(self._dev_attrs["drive"])

        if self.__vendor:
            self._dev_attrs["vendor"] = self.__vendor

        if self.__product:
            self._dev_attrs["product"] = self.__product

        if self.__rotation is not None and self.__rotation != "":
            self._dev_attrs["rotation"] = self.__rotation

        if self._channel is not None:
            self._dev_attrs["channel"] = self._channel

        if self._scsi_id is not None:
            self._dev_attrs["scsi-id"] = self._scsi_id

        if self._lun is not None:
            self._dev_attrs["lun"] = self._lun

        if self.__port_index:
            self._dev_attrs["port_index"] = self.__port_index

        if self.__port_wwn:
            self._dev_attrs["port_wwn"] = self.__port_wwn

        if self.__slot_number is not None:
            self._dev_attrs["slot_number"] = self.__slot_number

        if self.__atta_wwn:
            self._dev_attrs["atta_wwn"] = self.__atta_wwn

        if self.__atta_phy_id:
            self._dev_attrs["atta_phy_id"] = self.__atta_phy_id

        self.add_option(self.build_device_option(self._name, **self._dev_attrs))
