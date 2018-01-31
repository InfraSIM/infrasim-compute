'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
from infrasim import ArgsNotCorrect
from infrasim import run_command
from infrasim import config
from infrasim.model.core.element import CElement


class CBaseDrive(CElement):
    '''
    for most of the drive, the host options '-drive ...' are the same, so handle them in CBaseDrive,
    for the device option '-device ...', handle those options in the sub class according to the drive
    type, since different drives have the different attributes.
    '''
    def __init__(self):
        super(CBaseDrive, self).__init__()
        # protected
        self._name = None
        self._drive_info = None

        # store drive device option
        self._dev_attrs = {}
        self._host_opt = {}
        self.prefix = None

        # device option
        self.__index = 0
        self.__serial = None
        self.__wwn = None
        self.__bootindex = None
        self.__version = None
        self.__share_rw = "false"
        self.__page_file = None

        # host option
        self.__cache = None
        self.__aio = None
        self.__drive_file = None
        self.__format = None
        self.__l2_cache_size = None  # unit: byte
        self.__refcount_cache_size = None  # unit: byte
        self.__cluster_size = None  # unit: KB
        self.__preallocation_mode = None

        # other option
        self.__size = None

    @property
    def index(self):
        return self.__index

    @index.setter
    def index(self, idx):
        self.__index = idx

    def precheck(self):
        if self.__page_file and not os.path.exists(self.__page_file):
            raise ArgsNotCorrect("[CBaseDrive] page file {0} doesnot exist".format(self.__page_file))

        if self.__share_rw != "true" and self.__share_rw != "false":
            raise ArgsNotCorrect("[CBaseDrive] share-rw: {} is not a valid option [true/false]".format(self.__share_rw))

    @property
    def serial(self):
        return self.__serial

    @serial.setter
    def serial(self, s):
        self.__serial = s

    def get_uniq_name(self):
        return ""

    @property
    def dev_attrs(self):
        return self._dev_attrs

    @dev_attrs.setter
    def dev_attrs(self, s):
        self._dev_attrs = s

    @property
    def host_opt(self):
        return self._host_opt

    @host_opt.setter
    def host_opt(self, s):
        self._host_opt = s

    def init(self):
        self.__bootindex = self._drive_info.get("bootindex")
        self.__serial = self._drive_info.get("serial")
        self.__version = self._drive_info.get("version")
        self.__wwn = self._drive_info.get("wwn")
        self.__share_rw = self._drive_info.get("share-rw", "false")
        self.__page_file = self._drive_info.get("page-file")

        self.__format = self._drive_info.get("format", "qcow2")
        self.__cache = self._drive_info.get("cache", "writeback")
        self.__aio = self._drive_info.get("aio")
        self.__drive_file = self._drive_info.get("file")
        self.__l2_cache_size = self._drive_info.get("l2-cache-size")
        self.__refcount_cache_size = self._drive_info.get("refcount-cache-size")
        self.__cluster_size = self._drive_info.get("cluster-size")
        self.__preallocation_mode = self._drive_info.get("preallocation")

        self.__size = self._drive_info.get("size", 8)

        # assume the files starts with "/dev/" are block device
        # all the block devices are assumed to be raw format
        if self.__drive_file and self.__drive_file.startswith("/dev/"):
            self.__format = "raw"
        elif self.__drive_file is None:

            parent = self.owner
            while parent and not hasattr(parent, "get_workspace"):
                parent = parent.owner

            ws = None
            if hasattr(parent, "get_workspace"):
                ws = parent.get_workspace()

            if ws is None or not os.path.exists(ws):
                ws = ""

            # If user announce drive file in config, use it
            # else create for them.
            disk_file_base = os.path.join(config.infrasim_home, ws)
            self.__drive_file = os.path.join(disk_file_base, "disk-{}-{}.img".
                                             format(self.prefix, self.get_uniq_name()))

        if not os.path.exists(self.__drive_file):
            self.logger.info("[BaseDrive] Creating drive: {}".format(self.__drive_file))
            create_option_list = []
            if self.__cluster_size:
                create_option_list.append("=".join(["cluster_size", self.__cluster_size]))

            if self.__preallocation_mode:
                create_option_list.append("=".join(["preallocation", self.__preallocation_mode]))

            command = "qemu-img create -f {0} {1} {2}G".format(self.__format, self.__drive_file, self.__size)
            if len(create_option_list) > 0:
                command = "{} -o {}".format(command, ",".join(create_option_list))

            run_command(command)

    def build_host_option(self, *args, **kwargs):
        host_opt_list = []
        for k, v in kwargs.items():
            host_opt_list.append("{}={}".format(k, v))

        return "-drive {}".format(",".join(host_opt_list))

    def build_device_option(self, *args, **kwargs):
        name = args[0]
        device_opt_list = []
        device_opt_list.append("-device {}".format(name))
        for k, v in kwargs.items():
            device_opt_list.append("{}={}".format(k, v))

        return ",".join(device_opt_list)

    def handle_parms(self):
        # handle host option
        if self.__drive_file:
            self._host_opt["file"] = self.__drive_file

        if self.__format:
            self._host_opt["format"] = self.__format

        if self.__l2_cache_size:
            self._host_opt["l2-cache-size"] = self.__l2_cache_size

        if self.__refcount_cache_size:
            self._host_opt["refcount-cache-size"] = self.__l2_cache_size

        if self.__cache:
            self._host_opt["cache"] = self.__cache

        if self.__aio and self.__cache == "none":
            self._host_opt["aio"] = self.__aio

        # The following options are common for all kind of drives.

        # handle device options
        if self.__serial:
            self._dev_attrs["serial"] = self.__serial

        if self.__wwn:
            self._dev_attrs["wwn"] = self.__wwn

        if self.__version:
            self._dev_attrs["ver"] = self.__version

        if self.__bootindex:
            self._dev_attrs["bootindex"] = self.__bootindex

        if self.__page_file:
            self._dev_attrs["page_file"] = self.__page_file

        if self.__share_rw:
            self._dev_attrs["share-rw"] = self.__share_rw
