'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim.model.core.element import CElement


class CBaseStorageController(CElement):
    def __init__(self):
        super(CBaseStorageController, self).__init__()
        self._max_drive_per_controller = None
        self._drive_list = []
        self._pci_bus_nr = None
        self._ptm = None
        self._controller_info = None
        self._model = None
        self._attributes = {}
        # record the controller index inside this instance
        self.__controller_index = 0
        self._ses_list = []

        # remember the start index for the first controller
        # managed by this class
        self._start_idx = 0

    @property
    def controller_index(self):
        return self.__controller_index

    @controller_index.setter
    def controller_index(self, idx):
        self.__controller_index = idx

    def set_pci_bus_nr(self, nr):
        self._pci_bus_nr = nr

    def set_pci_topology_mgr(self, ptm):
        self._ptm = ptm

    def precheck(self):
        for drive_obj in self._drive_list:
            drive_obj.precheck()

    def init(self):
        self._model = self._controller_info.get('type')
        self._max_drive_per_controller = self._controller_info.get("max_drive_per_controller", 6)

    def _build_one_controller(self, *args, **kwargs):
        name = args[0]
        controller_option_list = []
        controller_option_list.append("-device {}".format(name))
        for k, v in kwargs.items():
            controller_option_list.append("{}={}".format(k, v))
        return ",".join(controller_option_list)

    def handle_parms(self):
        # drive_list IS empty when it connects a disk array.

        # handle drive options
        for drive_obj in self._drive_list:
            drive_obj.handle_parms()

        for ses_obj in self._ses_list:
            ses_obj.handle_parms()

        for drive_obj in self._drive_list:
            self.add_option(drive_obj.get_option())

        for ses_obj in self._ses_list:
            self.add_option(ses_obj.get_option())

        # controller attributes if there are some
        # common attributes for all controllers
        # add them into self._attributes here.

    def get_drvs_arg_option(self):
        if len(self._drive_list) == 0:
            return None
        if self._controller_info.get('connectors', None) is None:
            return None
        # handle drive options
        for drive_obj in self._drive_list:
            drive_obj.handle_parms()
        drv_args = []
        for drive_obj in self._drive_list[:]:
            drv_args.append(drive_obj.get_option())
            self._drive_list.remove(drive_obj)
        return drv_args, self._controller_info
