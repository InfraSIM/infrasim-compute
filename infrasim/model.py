'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
# Author:  Robert Xia <robert.xia@emc.com>,
# Forrest Gu <Forrest.Gu@emc.com>

import fcntl
import time
import shlex
import subprocess
import os
import uuid
import signal
import jinja2
import math
import shutil
import config
import json
import helper
import stat
import socket
from telnetlib import Telnet
from workspace import Workspace
from . import run_command, CommandRunFailed, ArgsNotCorrect, CommandNotFound, has_option
from infrasim.helper import run_in_namespace, double_fork
from .log import infrasim_log, LoggerType

logger_model = infrasim_log.get_logger(LoggerType.model.value)

"""
This module majorly defines infrasim element models.
For each element class, they need to implement methods:

    - __init__()
        Get initialized with element information;
        Define element attributes;
        Assign default value for certain attributes;
    - init()
        Parse information dict, assign to all attribute;
    - precheck()
        Validate attribute integrity and environment compatibility;
    - handle_parms()
        Add all attributes to command line options list;
    - get_option()
        Compose all options in list to a command line string;
"""


class Utility(object):
    @staticmethod
    @double_fork
    def execute_command(command, logger, log_path="",):
        args = shlex.split(command)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=False)

        flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        time.sleep(1)

        errout = None
        try:
            errout = proc.stderr.read()
        except IOError:
            pass
        if errout is not None:
            if log_path:
                with open(log_path, 'w') as fp:
                    fp.write(errout)
            else:
                logger.error(errout)

        if not os.path.isdir("/proc/{}".format(proc.pid)):
            logger.exception("command {} run failed".format(command))
            raise CommandRunFailed(command)

        return proc.pid

    @staticmethod
    def run_command(command):
        args = shlex.split(command)
        command_output = subprocess.check_output(args, shell=False)
        return command_output

    @staticmethod
    def get_working_directory():
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def ping_status(ip):
        rtn = True
        st = subprocess.call(['ping -c 3 %s >/dev/null' % ip], shell=True)
        if st:
            rtn = False
        return rtn


class CElement(object):
    def __init__(self):
        self.__option_list = []
        self.__owner = None
        self.__logger = infrasim_log.get_logger(LoggerType.model.value)

    @property
    def logger(self):
        return self.__logger

    @logger.setter
    def logger(self, logger):
        self.__logger = logger

    @property
    def owner(self):
        return self.__owner

    @owner.setter
    def owner(self, o):
        self.__owner = o

    def precheck(self):
        self.__logger.exception('Precheck is not implemented')
        raise NotImplementedError("precheck is not implemented")

    def init(self):
        self.__logger.exception('init is not implemented')
        raise NotImplementedError("init is not implemented")

    def handle_parms(self):
        self.__logger.exception('handle_parms is not implemented')
        raise NotImplementedError("handle_parms is not implemented")

    def add_option(self, option, pos=1):
        if option is None:
            return

        if option in self.__option_list:
            self.__logger.warning('option {} already added'.format(option))
            print "Warning: option {} already added.".format(option)
            return

        if pos == 0:
            self.__option_list.insert(0, option)
        else:
            self.__option_list.append(option)

    def get_option(self):
        if len(self.__option_list) == 0:
            self.__logger.exception("No option in the list")
            raise Exception("No option in the list")

        return " ".join(self.__option_list)


class CCPU(CElement):
    def __init__(self, cpu_info, socket_in_smbios=None):
        super(CCPU, self).__init__()
        self.__cpu = cpu_info
        self.__type = None
        self.__features = None
        self.__quantities = None
        self.__socket = socket_in_smbios

    def get_cpu_quantities(self):
        return self.__quantities

    def precheck(self):
        """
        Check if the CPU quantities exceeds the real physical CPU cores
        """
        if self.__quantities <= 0:
            self.logger.exception(
                '[CPU] quantities invalid: {}, should be positive'.
                format(self.__quantities))
            raise ArgsNotCorrect(
                '[CPU] quantities invalid: {}, should be positive'.
                format(self.__quantities))

        if self.__quantities % self.__socket != 0:
            self.logger.exception(
                '[CPU] quantities: {} is not divided by socket: {}'.
                format(self.__quantities, self.__socket))
            raise ArgsNotCorrect(
                '[CPU] quantities: {} is not divided by socket: {}'.
                format(self.__quantities, self.__socket))

    def init(self):
        self.__type = self.__cpu.get("type", "host")
        self.__quantities = self.__cpu.get('quantities', 2)
        self.__features = self.__cpu.get('features', "+vmx")

        if self.__socket is None:
            self.__socket = 2

    def handle_parms(self):
        if self.__features:
            cpu_option = "-cpu {0},{1}".format(self.__type, self.__features)
        else:
            cpu_option = "-cpu {}".format(self.__type)

        self.add_option(cpu_option)

        cores = self.__quantities / self.__socket
        smp_option = "-smp {vcpu_num},sockets={socket},cores={cores},threads=1".format(
                vcpu_num=self.__quantities, socket=self.__socket, cores=cores)

        self.add_option(smp_option)


class CCharDev(CElement):
    def __init__(self, chardev):
        super(CCharDev, self).__init__()
        self.__chardev = chardev
        self.__id = None
        self.__is_server = None
        self.__wait = None
        self.__path = None
        self.__backend_type = None  # should be socket/pipe/file/pty/stdio/ringbuffer/...
        self.__reconnect = None
        self.__host = None
        self.__port = None

    def set_id(self, chardev_id):
        self.__id = chardev_id

    @property
    def host(self):
        return self.__host

    @host.setter
    def host(self, h):
        self.__host = h

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, p):
        self.__port = p

    def get_id(self):
        return self.__id

    def get_path(self):
        return self.__path

    def precheck(self):
        if not self.__backend_type:
            self.logger.exception("[Chardev] Backend should be set.")
            raise ArgsNotCorrect("Backend of chardev should be set.")

        if self.__host and not helper.is_valid_ip(self.__host):
            self.logger.exception("[CharDev] Invalid chardev host: {}".format(self.__host))
            raise ArgsNotCorrect("Invalid chardev host: {}".format(self.__host))

        if self.__port:
            try:
                int(self.__port)
            except ValueError, e:
                self.logger.exception("[Chardev] Port is not a valid integer: {}".format(self.__port))
                raise ArgsNotCorrect("Port is not a valid integer: {}".format(self.__port))

            if helper.check_if_port_in_use("0.0.0.0", self.__port):
                self.logger.exception("[Chardev] Port {} is already in use".format(self.__port))
                raise ArgsNotCorrect("Port {} is already in use".format(self.__port))

        if self.__path:
            dir_path = os.path.dirname(self.__path)
            if not os.path.isdir(dir_path):
                self.logger.exception("[Chardev] Path folder doesn't exist: {}".format(dir_path))
                raise ArgsNotCorrect("Path folder doesn't exist: {}".format(dir_path))

    def init(self):
        self.__backend_type = self.__chardev.get('backend')
        self.__is_server = self.__chardev.get('server', False)
        self.__host = self.__chardev.get('host')
        self.__port = self.__chardev.get('port', self.__port)
        self.__wait = self.__chardev.get('wait', True)
        self.__path = self.__chardev.get('path')
        if not self.__is_server:
            self.__reconnect = self.__chardev.get('reconnect', 10)

    def handle_parms(self):
        chardev_option_list = []

        chardev_option_list.append(self.__backend_type)

        if self.__path is not None:
            chardev_option_list.append("path={}".format(self.__path))

        if self.__host is not None:
            chardev_option_list.append("host={}".format(self.__host))

        if self.__port is not None:
            chardev_option_list.append("port={}".format(self.__port))

        if self.__id is not None:
            chardev_option_list.append("id={}".format(self.__id))

        if self.__is_server:
            chardev_option_list.append("server")

        if self.__wait is False:
            chardev_option_list.append("nowait")

        if self.__reconnect is not None:
            chardev_option_list.append("reconnect={}".format(self.__reconnect))

        chardev_option = "-chardev {}".format(",".join(chardev_option_list))
        self.add_option(chardev_option)


class CMemory(CElement):
    def __init__(self, memory_info):
        super(CMemory, self).__init__()
        self.__memory = memory_info
        self.__memory_size = None

    def precheck(self):
        """
        Check if the memory size exceeds the system available size
        """
        if self.__memory_size is None:
            self.logger.exception("[Memory] Please set memory size.")
            raise ArgsNotCorrect("Please set memory size.")

    def init(self):
        self.__memory_size = self.__memory.get('size')

    def handle_parms(self):
        memory_option = "-m {}".format(self.__memory_size)
        self.add_option(memory_option)


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
        if len(self._drive_list) == 0:
            return

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


class LSISASController(CBaseStorageController):
    def __init__(self, controller_info):
        super(LSISASController, self).__init__()
        self._controller_info = controller_info
        self.__expander_count = None;
        self._iothread_id = None
        self.__expander_downstream_start_phy = None
        self.__expander_upstream_start_phy = None
        self.__expander_all_phys = None
        self.__use_msix = None

    def precheck(self):
        # call parent precheck()
        super(LSISASController, self).precheck()

    def init(self):
        super(LSISASController, self).init()

        self.__expander_count = self._controller_info.get("expander-count")
        self.__expander_downstream_start_phy = self._controller_info.get("expander-downstream-start-phy")
        self.__expander_upstream_start_phy = self._controller_info.get("expander-upstream-start-phy")
        self.__expander_all_phys = self._controller_info.get("expander-phys")
        self._iothread_id = self._controller_info.get("iothread")
        self.__use_msix = self._controller_info.get('use_msix')

        self._start_idx = self.controller_index
        idx = 0
        for drive_info in self._controller_info.get("drives", []):
            sd_obj = SCSIDrive(drive_info)
            sd_obj.logger = self.logger
            sd_obj.index = idx
            sd_obj.owner = self
            sd_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            sd_obj.set_scsi_id(idx % self._max_drive_per_controller)
            self._drive_list.append(sd_obj)
            idx += 1

        for ses_info in self._controller_info.get("seses", []):
            ses_obj = SESDevice(ses_info)
            ses_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            self._ses_list.append(ses_obj)

        for drive_obj in self._drive_list:
            drive_obj.init()

        for ses_obj in self._ses_list:
            ses_obj.init()

        # Update controller index, tell CBackendStorage what the controller index
        # should be for the next
        self.controller_index += (idx / self._max_drive_per_controller)

    def handle_parms(self):
        super(LSISASController, self).handle_parms()

        drive_nums = len(self._drive_list)
        cntrl_nums = int(math.ceil(float(drive_nums)/self._max_drive_per_controller)) or 1
        for cntrl_index in range(0, cntrl_nums):
            self._attributes["id"] = "scsi{}".format(self._start_idx + cntrl_index)
            if self.__expander_count:
                self._attributes["expander-count"] = self.__expander_count

            if self.__expander_downstream_start_phy is not None:
                self._attributes["downstream-start-phy"] = self.__expander_downstream_start_phy

            if self.__expander_upstream_start_phy is not None:
                self._attributes["upstream-start-phy"] = self.__expander_upstream_start_phy

            if self.__expander_all_phys is not None:
                self._attributes["expander-phys"] = self.__expander_all_phys

            if self._iothread_id:
                self._attributes["iothread"] = self._iothread_id

            if self.__use_msix is not None:
                self._attributes["use_msix"] = self.__use_msix

            self.add_option("{}".format(self._build_one_controller(self._model, **self._attributes)), 0)


class MegaSASController(CBaseStorageController):
    def __init__(self, controller_info):
        super(MegaSASController, self).__init__()
        self.__use_jbod = None
        self.__sas_address = None
        self.__use_msi = None
        self.__use_msix = None
        self.__max_cmds = None
        self.__max_sge = None
        self._controller_info = controller_info

    def precheck(self):
        # call parent precheck()
        super(MegaSASController, self).precheck()

    def init(self):
        # Call parent init()
        super(MegaSASController, self).init()

        self.__sas_address = self._controller_info.get('sas_address')
        self.__max_cmds = self._controller_info.get('max_cmds')
        self.__max_sge = self._controller_info.get('max_sge')
        self.__use_msi = self._controller_info.get('use_msi')
        self.__use_jbod = self._controller_info.get('use_jbod')

        self._start_idx = self.controller_index
        idx = 0
        for drive_info in self._controller_info.get("drives", []):
            sd_obj = SCSIDrive(drive_info)
            sd_obj.owner = self
            sd_obj.index = idx
            sd_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            sd_obj.set_scsi_id(idx % self._max_drive_per_controller)
            self._drive_list.append(sd_obj)
            idx += 1

        for drive_obj in self._drive_list:
            drive_obj.init()

        # Update controller index
        self.controller_index += (idx / self._max_drive_per_controller)

    def handle_parms(self):
        super(MegaSASController, self).handle_parms()

        drive_nums = len(self._drive_list)
        cntrl_nums = int(math.ceil(float(drive_nums)/self._max_drive_per_controller)) or 1

        bus_nr_generator = None

        if self._ptm:
            bus_nr_generator = self._ptm.get_available_bus()

        for cntrl_index in range(0, cntrl_nums):
            self._attributes["id"] = "scsi{}".format(self._start_idx + cntrl_index)
            if self.__use_jbod:
                self._attributes["use_jbod"] = self.__use_jbod

            if self.__sas_address:
                self._attributes["sas_address"] = self.__sas_address

            if self.__use_msi:
                self._attributes["use_msi"] = self.__use_msi

            if self.__max_cmds:
                self._attributes["max_cmds"] = self.__max_cmds

            if self.__max_sge:
                self._attributes["max_sge"] = self.__max_sge

            if bus_nr_generator:
                self._attributes["bus"] = "pci.{}".format(bus_nr_generator.next())
                self._attributes["addr"] = 0x1

            self.add_option("{}".format(self._build_one_controller(self._model, **self._attributes)), 0)


class AHCIController(CBaseStorageController):
    def __init__(self, controller_info):
        super(AHCIController, self).__init__()
        self._controller_info = controller_info
        self.__unit = 0

    def precheck(self):
        # call parent precheck()
        super(AHCIController, self).precheck()

    def init(self):
        super(AHCIController, self).init()

        self._start_idx = self.controller_index
        idx = 0
        for drive_info in self._controller_info.get("drives", []):
            ide_obj = IDEDrive(drive_info)
            ide_obj.logger = self.logger
            ide_obj.index = idx
            ide_obj.owner = self
            ide_obj.set_bus(self.controller_index + idx / self._max_drive_per_controller)
            ide_obj.set_scsi_id(idx % self._max_drive_per_controller)
            self._drive_list.append(ide_obj)
            idx += 1

        for drive_obj in self._drive_list:
            drive_obj.init()

        # Update controller index
        self.controller_index += (idx / self._max_drive_per_controller)

    def handle_parms(self):
        super(AHCIController, self).handle_parms()

        drive_nums = len(self._drive_list)
        cntrl_nums = int(math.ceil(float(drive_nums)/self._max_drive_per_controller)) or 1
        for cntrl_index in range(0, cntrl_nums):
            self._attributes["id"] = "sata{}".format(self._start_idx + cntrl_index)
            self.add_option("{}".format(self._build_one_controller(self._model, **self._attributes)), 0)


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
        self.prefix = None

        # private

        # device option
        self.__index = 0
        self.__serial = None
        self.__wwn = None
        self.__bootindex = None
        self.__bus_address = None
        self.__version = None

        # host option
        self.__cache = None
        self.__aio = None
        self.__drive_file = None
        self.__format = None
        self.__page_file = None

        # other option
        self.__size = None

        # identify a drive on which controller

        # self.__bus is controller index
        self.__bus = 0
        self._scsi_id = 0
        self._channel = 0
        self._lun = 0

        self.__l2_cache_size = None  # unit: byte
        self.__refcount_cache_size = None  # unit: byte
        self.__cluster_size = None  # unit: KB
        self.__preallocation_mode = None

    @property
    def index(self):
        return self.__index

    @index.setter
    def index(self, idx):
        self.__index = idx

    # controller index
    def set_bus(self, bus):
        self.__bus = bus

    def set_scsi_id(self, scsi_id):
        self._scsi_id = scsi_id

    def precheck(self):
        if self.__page_file and not os.path.exists(self.__page_file):
            self.logger.exception("[CBaseDrive] page file {0} doesnot exist".format(self.__page_file))
            raise ArgsNotCorrect("[CBaseDrive] page file {0} doesnot exist".format(self.__page_file))


    def init(self):
        self.__bootindex = self._drive_info.get("bootindex")
        self.__serial = self._drive_info.get("serial")
        self.__version = self._drive_info.get("version")
        self.__format = self._drive_info.get("format", "qcow2")
        self.__cache = self._drive_info.get("cache", "writeback")
        self.__aio = self._drive_info.get("aio")
        self.__size = self._drive_info.get("size", 8)
        self.__drive_file = self._drive_info.get("file")
        self.__wwn = self._drive_info.get("wwn")
        self.__page_file = self._drive_info.get("page-file")

        self.__l2_cache_size = self._drive_info.get("l2-cache-size")
        self.__refcount_cache_size = self._drive_info.get("refcount-cache-size")
        self.__cluster_size = self._drive_info.get("cluster-size")
        self.__preallocation_mode = self._drive_info.get("preallocation")

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
            self.__drive_file = os.path.join(disk_file_base, "disk{0}{1}.img".format(self.__bus, self.__index))

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


            try:
                run_command(command)
            except CommandRunFailed as e:
                self.logger.exception("[BaseDrive] {}".format(e.value))
                raise e

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
        host_opt = {}
        if self.__drive_file:
            host_opt["file"] = self.__drive_file

        if self.__format:
            host_opt["format"] = self.__format

        if self.__l2_cache_size:
            host_opt["l2-cache-size"] = self.__l2_cache_size

        if self.__refcount_cache_size:
            host_opt["refcount-cache-size"] = self.__l2_cache_size

        host_opt["if"] = "none"
        host_opt["id"] = "{}{}-{}-{}-{}".format(self.prefix, self.__bus, self._channel, self._scsi_id, self._lun)

        if self.__cache:
            host_opt["cache"] = self.__cache

        if self.__aio and self.__cache == "none":
            host_opt["aio"] = self.__aio

        self.add_option(self.build_host_option(**host_opt))

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

        # for ATA controller, one bus should only have one target, AHCI could support at most 6 target devices
        # for SCSI controller, one controller only one Bus which could support at most 8 target devices
        if self.__bus_address is None:
            b = self._scsi_id if self.prefix == "sata" else self._channel
            self.__bus_address = "{}{}.{}".format(self.prefix, self.__bus, b)

        self._dev_attrs["bus"] = self.__bus_address

        self._dev_attrs["drive"] = "{}{}-{}-{}-{}".format(self.prefix, self.__bus,
                                                          self._channel, self._scsi_id, self._lun)

        self._dev_attrs["id"] = "dev-{}".format(self._dev_attrs["drive"])

        if self.__page_file:
            self._dev_attrs["page_file"] = self.__page_file


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

    def precheck(self):
        super(SCSIDrive, self).precheck()

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

    def handle_parms(self):
        super(SCSIDrive, self).handle_parms()

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

        self.add_option(self.build_device_option(self._name, **self._dev_attrs))


class IDEDrive(CBaseDrive):
    def __init__(self, drive_info):
        super(IDEDrive, self).__init__()
        self._name = "ide-hd"
        self.prefix = "sata"
        self._drive_info = drive_info
        self.__model = None
        self.__unit = None

    def set_unit(self, unit):
        self.__unit = unit

    def init(self):
        super(IDEDrive, self).init()

        self.__model = self._drive_info.get("model")

    def handle_parms(self):
        super(IDEDrive, self).handle_parms()

        if self.__model:
            self._dev_attrs["model"] = self.__model

        if self.__unit is not None:
            self._dev_attrs["unit"] = self.__unit

        self.add_option(self.build_device_option(self._name, **self._dev_attrs))


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


class CBackendStorage(CElement):
    def __init__(self, backend_storage_info):
        super(CBackendStorage, self).__init__()
        self.__backend_storage_info = backend_storage_info
        self.__controller_list = []
        self.__pci_topology_manager = None

        # Global controller index managed by CBackendStorage
        self.__sata_controller_index = 0
        self.__scsi_controller_index = 0

    def set_pci_topology_mgr(self, ptm):
        self.__pci_topology_manager = ptm

    def precheck(self):
        for controller_obj in self.__controller_list:
            controller_obj.precheck()

    def __create_controller(self, controller_info):
        controller_obj = None
        model = controller_info.get("type", "ahci")
        if model.startswith("megasas"):
            controller_obj = MegaSASController(controller_info)
        elif model.startswith("lsi"):
            controller_obj = LSISASController(controller_info)
        elif "ahci" in model:
            controller_obj = AHCIController(controller_info)
        else:
            self.logger.exception("[BackendStorage] Unsupported controller type")
            raise ArgsNotCorrect("Unsupported controller type.")

        controller_obj.logger = self.logger
        # set owner
        controller_obj.owner = self
        return controller_obj

    def init(self):
        for controller in self.__backend_storage_info:
            controller_obj = self.__create_controller(controller)
            if self.__pci_topology_manager:
                controller_obj.set_pci_topology_mgr(self.__pci_topology_manager)
            self.__controller_list.append(controller_obj)

        for controller_obj in self.__controller_list:
            if isinstance(controller_obj, AHCIController):
                controller_obj.controller_index = self.__sata_controller_index
            else:
                controller_obj.controller_index = self.__scsi_controller_index

            controller_obj.init()

            if isinstance(controller_obj, AHCIController):
                self.__sata_controller_index = controller_obj.controller_index + 1
            else:
                self.__scsi_controller_index = controller_obj.controller_index + 1

    def handle_parms(self):
        for controller_obj in self.__controller_list:
            controller_obj.handle_parms()

        for controller_obj in self.__controller_list:
            self.add_option(controller_obj.get_option())


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

    def set_index(self, index):
        self.__index = index

    def precheck(self):
        # Check if parameters are valid
        # bridge exists?
        if self.__network_mode == "bridge":
            if self.__bridge_name is None:
                if "br0" not in helper.get_all_interfaces():
                    self.logger.exception('[Network] network_name(br0) is not exists')
                    raise ArgsNotCorrect("ERROR: network_name(br0) is not exists")
            else:
                if self.__bridge_name not in helper.get_all_interfaces():
                    self.logger.exception('[Network] network_name({}) is not exists'.
                                          format(self.__bridge_name))
                    raise ArgsNotCorrect("ERROR: network_name({}) is not exists".
                                         format(self.__bridge_name))
            if "mac" not in self.__network:
                self.logger.exception("[Network] mac address is not specified for"
                                      "target network:\n{}".
                                      format(json.dumps(self.__network, indent=4)))
                raise ArgsNotCorrect("ERROR: mac address is not specified for "
                                     "target network:\n{}".
                                     format(json.dumps(self.__network, indent=4)))
            else:
                list_addr = self.__mac_address.split(":")
                if len(list_addr) != 6:
                    self.logger.exception("[Network] mac address invalid: {}".
                                          format(self.__mac_address))
                    raise ArgsNotCorrect("ERROR: mac address invalid: {}".
                                         format(self.__mac_address))
                for each_addr in list_addr:
                    try:
                        int(each_addr, 16)
                    except:
                        self.logger.exception("[Network] mac address invalid: {}".
                                              format(self.__mac_address))
                        raise ArgsNotCorrect("ERROR: mac address invalid: {}".
                                             format(self.__mac_address))

    def init(self):
        self.__network_mode = self.__network.get('network_mode', "nat")
        self.__bridge_name = self.__network.get('network_name')
        self.__nic_name = self.__network.get('device')
        self.__mac_address = self.__network.get('mac')

    def handle_parms(self):
        if self.__network_mode == "bridge":
            if self.__bridge_name is None:
                self.__bridge_name = "br0"

            qemu_sys_prefix = os.path.dirname(
                Utility.run_command("which qemu-system-x86_64")
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
            self.logger.exception("[Network] {} is not supported now.".
                                  format(self.__network_mode))
            raise Exception("ERROR: {} is not supported now.".
                            format(self.__network_mode))

        nic_option = ",".join(["{}".format(self.__nic_name),
                               "netdev=netdev{}".format(self.__index),
                               "mac={}".format(self.__mac_address)])

        network_option = " ".join(["-netdev {}".format(netdev_option),
                                   "-device {}".format(nic_option)])
        self.add_option(network_option)


class CBackendNetwork(CElement):
    def __init__(self, network_info_list):
        super(CBackendNetwork, self).__init__()
        self.__backend_network_list = network_info_list

        self.__network_list = []

    def precheck(self):
        for network_obj in self.__network_list:
            try:
                network_obj.precheck()
            except ArgsNotCorrect as e:
                self.logger.exception('[BackendNetwork] {}'.format(e.value))
                raise e

    def init(self):
        index = 0
        for network in self.__backend_network_list:
            network_obj = CNetwork(network)
            network_obj.logger = self.logger
            network_obj.set_index(index)
            self.__network_list.append(network_obj)
            index += 1

        for network_obj in self.__network_list:
            network_obj.init()

    def handle_parms(self):
        for network_obj in self.__network_list:
            network_obj.handle_parms()

        for network_obj in self.__network_list:
            self.add_option(network_obj.get_option())


class CIPMI(CElement):
    def __init__(self, ipmi_info):
        super(CIPMI, self).__init__()
        self.__ipmi = ipmi_info
        self.__interface = None
        self.__host = None
        self.__bmc_connection_port = None
        self.__chardev_obj = None
        self.__ioport = None
        self.__irq = None

    def set_bmc_conn_host(self, host):
        self.__host = host

    def set_bmc_conn_port(self, port):
        self.__bmc_connection_port = port

    def precheck(self):
        """
        Check if internal socket port is used.
        """
        if self.__chardev_obj is None:
            self.logger.exception("[IPMI] -chardev should set.")
            raise Exception("-chardev should set.")

    def init(self):
        self.__interface = self.__ipmi.get('interface')

        if 'chardev' in self.__ipmi:
            self.__chardev_obj = CCharDev(self.__ipmi['chardev'])
            self.__chardev_obj.logger = self.logger
            self.__chardev_obj.set_id("ipmi0")
            self.__chardev_obj.host = self.__host
            self.__chardev_obj.port = self.__bmc_connection_port
            self.__chardev_obj.init()

        self.__ioport = self.__ipmi.get('ioport')
        self.__irq = self.__ipmi.get('irq')

    def handle_parms(self):
        self.__chardev_obj.handle_parms()
        chardev_option = self.__chardev_obj.get_option()
        bmc_option = ','.join(['ipmi-bmc-extern', 'chardev={}'.format(self.__chardev_obj.get_id()), 'id=bmc0'])
        interface_option = ','.join(['isa-ipmi-kcs', 'bmc=bmc0'])
        if self.__ioport:
            interface_option = ','.join([interface_option, "ioport={}".format(self.__ioport)])

        if self.__irq:
            interface_option = ','.join([interface_option, "irq={}".format(self.__irq)])

        ipmi_option = " ".join([chardev_option,
                                "-device {}".format(bmc_option),
                                "-device {}".format(interface_option)])
        self.add_option(ipmi_option)


class CPCIBridge(CElement):
    def __init__(self, bridge_info):
        super(CPCIBridge, self).__init__()
        self.__bridge_info = bridge_info
        self.__children_bridge_list = None
        self.__current_bridge_device = None
        self.__addr = None
        self.__bus = None
        self.__parent = None
        self.__can_use_bus = False
        self.__chassis_nr = None
        self.__msi = None
        self.__multifunction = None

    def set_bus(self, bus_nr):
        self.__bus = bus_nr

    def get_bus(self):
        return self.__bus

    def get_bus_list(self):
        bus_list = []
        for br_obj in self.__children_bridge_list:
            if br_obj.__can_use_bus:
                bus_list.append(br_obj.get_bus())
        return bus_list

    def set_parent(self, parent):
        self.__parent = parent

    def get_parent(self):
        return self.__parent

    def precheck(self):
        if self.__current_bridge_device is None:
            self.logger.exception("[PCIBridge] bridge device is required.")
            raise ArgsNotCorrect("bridge device is required.")

    def init(self):
        self.__current_bridge_device = self.__bridge_info.get('device')
        self.__addr = self.__bridge_info.get('addr')
        self.__chassis_nr = self.__bridge_info.get('chassis_nr')
        self.__msi = self.__bridge_info.get('msi')
        self.__multifunction = self.__bridge_info.get('multifunction')

        if 'downstream_bridge' not in self.__bridge_info:
            return

        self.__children_bridge_list = []
        current_bus_nr = self.__bus + 1
        for child_br in self.__bridge_info['downstream_bridge']:
            child_obj = CPCIBridge(child_br)
            child_obj.logger = self.logger
            child_obj.set_bus(current_bus_nr)
            child_obj.__can_use_bus = True
            child_obj.set_parent("pci.{}".format(self.__bus))
            self.__children_bridge_list.append(child_obj)
            current_bus_nr += 1

        for child_obj in self.__children_bridge_list:
            child_obj.init()

    def handle_parms(self):
        bridge_option = "-device {},bus={},id=pci.{}".format(
                            self.__current_bridge_device,
                            self.__parent,
                            self.__bus
                            )
        if self.__addr:
            bridge_option = ",".join([bridge_option, "addr={}".format(self.__addr)])

        if self.__chassis_nr:
            bridge_option = ",".join([bridge_option, "chassis_nr={}".format(self.__chassis_nr)])

        if self.__msi:
            bridge_option = ",".join([bridge_option, "msi={}".format(self.__msi)])

        if self.__multifunction:
            bridge_option = ",".join([bridge_option, "multifunction={}".format(self.__multifunction)])

        self.add_option(bridge_option)

        if self.__children_bridge_list is None:
            return

        for child_obj in self.__children_bridge_list:
            child_obj.handle_parms()

        for child_obj in self.__children_bridge_list:
            self.add_option(child_obj.get_option())


class CPCITopologyManager(CElement):
    def __init__(self, pci_topology_info):
        super(CPCITopologyManager, self).__init__()
        self.__pci_topology_info = pci_topology_info
        self.__bridge_list = []
        self.__available_bus_list = []

    def get_available_bus(self):
        for bus_nr in self.__available_bus_list:
            yield bus_nr

    def precheck(self):
        pass

    def init(self):
        current_bus_nr = 1
        for bri in self.__pci_topology_info:
            bridge_obj = CPCIBridge(bri)
            bridge_obj.logger = self.logger
            bridge_obj.set_bus(current_bus_nr)
            bridge_obj.set_parent("pcie.0")
            self.__bridge_list.append(bridge_obj)
            current_bus_nr += 1

        for br_obj in self.__bridge_list:
            br_obj.init()

        for br_obj in self.__bridge_list:
            self.__available_bus_list.extend(br_obj.get_bus_list())

    def handle_parms(self):
        for br_obj in self.__bridge_list:
            br_obj.handle_parms()

        for br_obj in self.__bridge_list:
            self.add_option(br_obj.get_option())


class CMonitor(CElement):
    def __init__(self, monitor_info):
        super(CMonitor, self).__init__()
        self.__monitor = monitor_info
        self.__chardev = None
        self.__mode = "readline"
        self.__workspace = ""
        self.__monitor_handle = None

    def get_workspace(self):
        return self.__workspace

    def set_workspace(self, ws):
        self.__workspace = ws

    def precheck(self):
        if self.__mode not in ["readline", "control"]:
            self.logger.exception("[Monitor] Invalid monitor mode: {}".format(self.__mode))
            raise ArgsNotCorrect("Invalid monitor mode: {}".format(self.__mode))

        try:
            self.__chardev.precheck()
        except ArgsNotCorrect, e:
            self.logger.exception("[Monitor] {}".format(e.value))
            print e.value
            raise e

        # Monitor specific chardev attribution
        if self.__monitor["chardev"]["backend"] != "socket":
            self.logger.exception("[Monitor] Invalid monitor chardev backend: {}".
                                    format(self.__monitor["chardev"]["backend"]))
            raise ArgsNotCorrect("Invalid monitor chardev backend: {}".
                                    format(self.__monitor["chardev"]["backend"]))
        if self.__monitor["chardev"]["server"] is not True:
            self.logger.exception("[Monitor] Invalid monitor chardev server: {}".
                                    format(self.__monitor["chardev"]["server"]))
            raise ArgsNotCorrect("Invalid monitor chardev server: {}".
                                    format(self.__monitor["chardev"]["server"]))
        if self.__monitor["chardev"]["wait"] is not False:
            self.logger.exception("[Monitor] Invalid monitor chardev wait: {}".
                                    format(self.__monitor["chardev"]["wait"]))
            raise ArgsNotCorrect("Invalid monitor chardev wait: {}".
                                    format(self.__monitor["chardev"]["wait"]))


    def init(self):
        self.__mode = self.__monitor.get("mode", "readline")
        chardev_info = {}
        if self.__mode == "readline":
            chardev_info = self.__monitor.get("chardev", {})
            if "backend" not in chardev_info:
                chardev_info["backend"] = "socket"
            if "server" not in chardev_info:
                chardev_info["server"] = True
            if "wait" not in chardev_info:
                chardev_info["wait"] = False
            if "host" not in chardev_info:
                chardev_info["host"] = "127.0.0.1"
            if "port" not in chardev_info:
                chardev_info["port"] = 2345
        elif self.__mode == "control":
            chardev_info = self.__monitor.get("chardev", {})
            if "backend" not in chardev_info:
                chardev_info["backend"] = "socket"
            if "server" not in chardev_info:
                chardev_info["server"] = True
            if "wait" not in chardev_info:
                chardev_info["wait"] = False
            if "path" not in chardev_info:
                if self.get_workspace():
                    chardev_path = os.path.join(self.get_workspace(), ".monitor")
                else:
                    chardev_path = os.path.join(config.infrasim_etc, ".monitor")
                chardev_info["path"] = chardev_path
        else:
            pass

        self.__monitor["chardev"] = chardev_info
        self.__chardev = CCharDev(chardev_info)
        self.__chardev.logger = self.logger
        self.__chardev.set_id("monitorchardev")
        self.__chardev.init()

    def handle_parms(self):
        self.__chardev.handle_parms()
        self.add_option(self.__chardev.get_option())
        self.add_option("-mon chardev={},mode={}".format(self.__chardev.get_id(), self.__mode))

    def get_mode(self):
        return self.__mode

    def open(self):
        if self.__mode == "readline":
            self.__monitor_handle = Telnet(self.__chardev.host, self.__chardev.port)
        elif self.__mode == "control":
            self.__monitor_handle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.__monitor_handle.connect(self.__chardev.get_path())

            # enable qmp capabilities
            qmp_payload = {
                "execute": "qmp_capabilities"
            }
            self.send(qmp_payload)
        else:
            raise ArgsNotCorrect("[Monitor] Monitor mode {} is unknown.".format(self.__mode))
        self.logger.info("[Monitor] monitor opened({}).".format(self.__monitor_handle))

    def send(self, command):
        if self.__monitor_handle:
            self.logger.info("[Monitor] send command {}".format(command))
            if self.__mode == "readline":
                self.__monitor_handle.write(command)
            else:
                self.__monitor_handle.send(json.dumps(command))

    def close(self):
        if self.__monitor_handle:
            self.__monitor_handle.close()
            self.logger.info("[Monitor] monitor closed.")

class Task(object):
    def __init__(self):
        # priroty should be range from 0 to 5
        # +-----+-----+-----+----+-----+
        # |  0  |  1  |  2  |  3 |  4  |
        # +-----+-----+-----+----+-----+
        # |High |                | Low |
        # +-----+-----+-----+----+-----+
        self.__task_priority = None
        self.__workspace = None
        self.__task_name = None
        self.__log_path = ""
        self.__logger = infrasim_log.get_logger(LoggerType.model.value)

        # If any task set the __asyncronous to True,
        # this task shall only be maintained with information
        # no actual run shall be taken
        self.__asyncronous = False
        self.__netns = None

    @property
    def netns(self):
        return self.__netns

    @netns.setter
    def netns(self, ns):
        self.__netns = ns

    def set_priority(self, priority):
        self.__task_priority = priority

    def get_priority(self):
        return self.__task_priority

    def set_task_name(self, name):
        self.__task_name = name

    def get_task_name(self):
        return self.__task_name

    def get_commandline(self):
        self.__logger.exception("get_commandline not implemented")
        raise NotImplementedError("get_commandline not implemented")

    def set_workspace(self, directory):
        self.__workspace = directory

    def get_workspace(self):
        return self.__workspace

    def set_log_path(self, log_path):
        self.__log_path = log_path

    @property
    def logger(self):
        return self.__logger

    @logger.setter
    def logger(self, logger):
        self.__logger = logger

    def set_asyncronous(self, asyncr):
        self.__asyncronous = asyncr

    def get_pid_file(self):
        return "{}/.{}.pid".format(self.__workspace, self.__task_name)

    def get_task_pid(self):
        try:
            with open(self.get_pid_file(), "r") as f:
                pid = f.readline().strip()
        except Exception:
            return -1

        if pid == "":
            return -1

        return pid

    def _task_is_running(self):
        pid = self.get_task_pid()
        if pid > 0 and os.path.exists("/proc/{}".format(pid)):
            return True
        return False

    @run_in_namespace
    def run(self):

        if self.__asyncronous:
            start = time.time()
            while True:
                if self._task_is_running():
                    break

                if time.time()-start > 10:
                    break

            if not self._task_is_running():
                print "[ {} ] {} fail to start".\
                    format("ERROR", self.__task_name)
                self.__logger.error("[ {} ] {} fail to start".
                                    format("ERROR", self.__task_name))
            else:
                print "[ {:<6} ] {} is running".format(self.get_task_pid(), self.__task_name)
                self.__logger.info("[ {:<6} ] {} is running".
                                   format(self.get_task_pid(), self.__task_name))
            return

        cmdline = self.get_commandline()

        self.__logger.info("{}'s command line: {}".
                           format(self.__task_name, cmdline))

        pid_file = self.get_pid_file()

        if self._task_is_running():
            print "[ {:<6} ] {} is already running".format(
                self.get_task_pid(), self.__task_name)
            self.__logger.info("[ {:<6} ] {} is already running".
                               format(self.get_task_pid(), self.__task_name))
            return
        elif os.path.exists(pid_file):
            # If the qemu quits exceptionally when starts, pid file is also
            # created, but actually the qemu died.
            os.remove(pid_file)

        pid = Utility.execute_command(cmdline, self.__logger, log_path=self.__log_path)

        print "[ {:<6} ] {} starts to run".format(pid, self.__task_name)
        self.__logger.info("[ {:<6} ] {} starts to run".format(pid, self.__task_name))

        with open(pid_file, "w") as f:
            if os.path.exists("/proc/{}".format(pid)):
                f.write("{}".format(pid))

    def terminate(self):
        task_pid = self.get_task_pid()
        pid_file = self.get_pid_file()
        try:
            if task_pid > 0:
                os.kill(int(task_pid), signal.SIGTERM)
                print "[ {:<6} ] {} stop".format(task_pid, self.__task_name)
                self.__logger.info("[ {:<6} ] {} stop".
                                   format(task_pid, self.__task_name))
                time.sleep(1)
                if os.path.exists("/proc/{}".format(task_pid)):
                    os.kill(int(task_pid), signal.SIGKILL)
            else:
                print "[ {:<6} ] {} is stopped".format("", self.__task_name)
                self.__logger.info("[ {:<6} ] {} is stopped".
                                   format("", self.__task_name))

            if os.path.exists(pid_file):
                os.remove(pid_file)
        except OSError:
            if os.path.exists(pid_file):
                os.remove(pid_file)
            if not os.path.exists("/proc/{}".format(task_pid)):
                print "[ {:<6} ] {} is stopped".format(task_pid, self.__task_name)
                self.__logger.info("[ {:<6} ] {} is stopped".
                                   format(task_pid, self.__task_name))
            else:
                print("[ {:<6} ] {} stop failed.".
                      format(task_pid, self.__task_name))
                self.__logger.info("[ {:<6} ] {} stop failed.".
                                   format(task_pid, self.__task_name))

    def status(self):
        task_pid = self.get_task_pid()
        pid_file = "{}/.{}.pid".format(self.__workspace, self.__task_name)
        if not os.path.exists(pid_file):
            print("{} is stopped".format(self.__task_name))
        elif not os.path.exists("/proc/{}".format(task_pid)):
            print("{} is stopped".format(self.__task_name))
            os.remove(pid_file)
        else:
            task_pid = self.get_task_pid()
            if task_pid > 0:
                print "[ {:<6} ] {} is running".\
                    format(task_pid, self.__task_name)


class CCompute(Task, CElement):

    numactl = None

    def __init__(self, compute_info):
        super(CCompute, self).__init__()
        CElement.__init__(self)
        self.__compute = compute_info
        self.__element_list = []
        self.__enable_kvm = True
        self.__smbios = None
        self.__bios = None
        self.__boot_order = None
        self.__boot_menu = None
        self.__boot_splash_name = None
        self.__boot_splash_time = None
        self.__qemu_bin = "qemu-system-x86_64"
        self.__cdrom_file = None
        self.__vendor_type = None
        # remember cpu object
        self.__cpu_obj = None
        self.__numactl_info = False
        self.__numactl_mode = None
        self.__cdrom_file = None
        self.__monitor = None
        self.__display = None

        # Node wise attributes
        self.__port_qemu_ipmi = 9002
        self.__socket_serial = ""
        self.__sol_enabled = False
        self.__kernel = None
        self.__initrd = None
        self.__cmdline = None
        self.__mem_path = None
        self.__extra_option = None
        self.__iommu = False
        self.__monitor = None

        self.__force_shutdown = None

    def enable_sol(self, enabled):
        self.__sol_enabled = enabled

    def set_type(self, vendor_type):
        self.__vendor_type = vendor_type

    def set_port_qemu_ipmi(self, port):
        self.__port_qemu_ipmi = port

    def set_socket_serial(self, o):
        self.__socket_serial = o

    def set_smbios(self, smbios):
        self.__smbios = smbios

    def get_smbios(self):
        return self.__smbios

    @run_in_namespace
    def precheck(self):
        # check if qemu-system-x86_64 exists
        try:
            run_command("which {}".format(self.__qemu_bin))
        except CommandRunFailed:
            self.logger.exception("[Compute] Can not find file {}".format(self.__qemu_bin))
            raise CommandNotFound(self.__qemu_bin)

        # check if smbios exists
        if not os.path.isfile(self.__smbios):
            self.logger.exception("[Compute] Target SMBIOS file doesn't exist: {}".
                                  format(self.__smbios))
            raise ArgsNotCorrect("Target SMBIOS file doesn't exist: {}".format(self.__smbios))

        if self.__kernel and os.path.exists(self.__kernel) is False:
            self.logger.exception("[Compute] Kernel {} does not exist.".
                                  format(self.__kernel))
            raise ArgsNotCorrect("Kernel {} does not exist.".format(self.__kernel))

        if self.__initrd and os.path.exists(self.__initrd) is False:
            self.logger.exception("[Compute] Kernel {} does not exist.".
                                  format(self.__initrd))
            raise ArgsNotCorrect("Kernel {} does not exist.".format(self.__initrd))

        # check if VNC port is in use
        if helper.check_if_port_in_use("0.0.0.0", self.__display + 5900):
            self.logger.exception("[Compute] VNC port {} is already in use.".
                                  format(self.__display + 5900))
            raise ArgsNotCorrect("VNC port {} is already in use.".
                                 format(self.__display + 5900))

        # check sub-elements
        for element in self.__element_list:
            try:
                element.precheck()
            except Exception as e:
                self.logger.exception("[Compute] {}".format(str(e)))
                raise e

        if 'boot' in self.__compute:
            if 'menu' in self.__compute['boot']:
                if isinstance(self.__compute['boot']['menu'], str):
                    menu_option = str(self.__compute['boot']['menu']).strip(" ").lower()
                    if menu_option not in ["on", "off"]:
                        msg = "Error: illegal config option. " \
                              "The 'menu' must be either 'on' or 'off'."
                        self.logger.exception(msg)
                        raise ArgsNotCorrect(msg)
                elif not isinstance(self.__compute['boot']['menu'], bool):
                    msg = "Error: illegal config option. The 'menu' " \
                          "must be either 'on' or 'off'."
                    self.logger.exception(msg)
                    raise ArgsNotCorrect(msg)

    @run_in_namespace
    def init(self):
        if 'kvm_enabled' in self.__compute and not helper.check_kvm_existence():
            self.__enable_kvm = False
        else:
            self.__enable_kvm = helper.check_kvm_existence()

        if 'smbios' in self.__compute:
            self.__smbios = self.__compute['smbios']
        elif self.get_workspace():
            self.__smbios = os.path.join(self.get_workspace(),
                                         "data",
                                         "{}_smbios.bin".
                                         format(self.__vendor_type))
        else:
            self.__smbios = os.path.join(config.infrasim_data,
                                         "{0}/{0}_smbios.bin".format(self.__vendor_type))

        self.__bios = self.__compute.get('bios')
        if 'boot' in self.__compute:
            self.__boot_order = self.__compute['boot'].get('boot_order', "ncd")
            if 'menu' in self.__compute['boot']:
                self.__boot_menu = "on" if self.__compute['boot']['menu'] in [True, 'on'] else "off"
            self.__boot_splash_name = self.__compute['boot'].get('splash', None)
            self.__boot_splash_time = self.__compute['boot'].get('splash-time', None)
        else:
            self.__boot_order = "ncd"

        self.__cdrom_file = self.__compute.get('cdrom')

        self.__numactl_info = self.__compute.get("numa_control")
        if self.__numactl_info and os.path.exists("/usr/bin/numactl"):
            self.__numactl_mode = self.__numactl_info.get("mode", "auto")
            if self.__class__.numactl is None:
                self.__class__.numactl = NumaCtl()


            self.logger.info('[compute] infrasim has '
                                'enabled numa control')
        else:
            self.logger.info('[compute] infrasim can\'t '
                                'find numactl in this environment')

        self.__display = self.__compute.get('vnc_display', 1)
        self.__kernel = self.__compute.get('kernel')
        self.__initrd = self.__compute.get('initrd')

        self.__cmdline = self.__compute.get("cmdline")

        self.__mem_path = self.__compute.get("mem_path")

        self.__extra_option = self.__compute.get("extra_option")
        self.__qemu_bin = self.__compute.get("qemu_bin", self.__qemu_bin)
        self.__iommu = self.__compute.get("iommu")
        self.__force_shutdown = self.__compute.get("force_shutdown", True)

        cpu_obj = CCPU(self.__compute['cpu'])
        cpu_obj.logger = self.logger
        self.__element_list.append(cpu_obj)
        self.__cpu_obj = cpu_obj

        memory_obj = CMemory(self.__compute['memory'])
        memory_obj.logger = self.logger
        self.__element_list.append(memory_obj)

        # If PCI device wants to sit on one specific PCI bus, the bus should be
        # created first prior to using the bus, here we always create the PCI
        # bus prior to other PCI devices' creation
        pci_topology_manager_obj = None
        if 'pci_bridge_topology' in self.__compute:
            pci_topology_manager_obj = CPCITopologyManager(self.__compute['pci_bridge_topology'])
            pci_topology_manager_obj.logger = self.logger
            self.__element_list.append(pci_topology_manager_obj)

        backend_storage_obj = CBackendStorage(self.__compute['storage_backend'])
        backend_storage_obj.logger = self.logger
        backend_storage_obj.owner = self
        if pci_topology_manager_obj:
            backend_storage_obj.set_pci_topology_mgr(pci_topology_manager_obj)
        backend_storage_obj.owner = self
        self.__element_list.append(backend_storage_obj)

        backend_network_obj = CBackendNetwork(self.__compute['networks'])
        backend_network_obj.logger = self.logger
        self.__element_list.append(backend_network_obj)

        if has_option(self.__compute, "ipmi"):
            ipmi_obj = CIPMI(self.__compute['ipmi'])
        else:
            ipmi_info = {
                'interface': 'kcs',
                'chardev': {
                    'backend': 'socket',
                    'host': '127.0.0.1',
                }
            }
            ipmi_obj = CIPMI(ipmi_info)
        ipmi_obj.logger = self.logger
        ipmi_obj.set_bmc_conn_port(self.__port_qemu_ipmi)
        self.__element_list.append(ipmi_obj)

        if self.__compute.get('monitor', ''):
            self.__monitor = CMonitor(self.__compute['monitor'])
        else:
            self.__monitor = CMonitor({
                'mode': 'readline',
                'chardev': {
                    'backend': 'socket',
                    'host': '127.0.0.1',
                    'port': 2345,
                    'server': True,
                    'wait': False
                }
            })
        self.__monitor.set_workspace(self.get_workspace())
        self.__monitor.logger = self.logger
        self.__element_list.append(self.__monitor)
        for element in self.__element_list:
            element.init()

    def get_commandline(self):
        # handle params
        self.handle_parms()

        qemu_commandline = ""
        for element_obj in self.__element_list:
            qemu_commandline = " ".join([qemu_commandline, element_obj.get_option()])

        qemu_commandline = " ".join([self.__qemu_bin, self.get_option(), qemu_commandline])

        # set cpu affinity
        if self.__numactl_mode == "auto":
            cpu_number = self.__cpu_obj.get_cpu_quantities()
            try:
                bind_cpu_list = [str(x) for x in self.__class__.numactl.get_cpu_list(cpu_number)]
            except Exception, e:
                bind_cpu_list = []
                self.logger.warning('[Compute] {}'.format(str(e)))
            if len(bind_cpu_list) > 0:
                numactl_option = 'numactl --physcpubind={} --localalloc'.format(','.join(bind_cpu_list))
                qemu_commandline = " ".join([numactl_option, qemu_commandline])
        elif self.__numactl_mode == "manual":
            bind_cpu_list = self.__numactl_info.get("cores").split(",")
            numactl_option = 'numactl --physcpubind={} --localalloc'.format(self.__numactl_info.get("cores"))
            mem_node_id = self.__numactl_info.get("node-id")
            if mem_node_id is not None:
                numactl_option = " ".join([numactl_option, "--membind={}".format(mem_node_id)])
            qemu_commandline = " ".join([numactl_option, qemu_commandline])

        return qemu_commandline

    def handle_parms(self):
        self.add_option("-vnc :{}".format(self.__display))
        self.add_option("-name {}".format(self.get_task_name()))
        self.add_option("-device sga")

        if self.__enable_kvm:
            self.add_option("--enable-kvm")

        if self.__smbios:
            self.add_option("-smbios file={}".format(self.__smbios))

        if self.__bios:
            self.add_option("-bios {}".format(self.__bios))

        if self.__mem_path:
            self.add_option("-mem-path {}".format(self.__mem_path))

        if self.__extra_option:
            self.add_option(self.__extra_option)

        boot_param = []
        if self.__boot_order:
            bootdev_path = self.get_workspace() + '/bootdev'
            if os.path.exists(bootdev_path) is True:
                with open(bootdev_path, "r") as f:
                    boot_param = f.readlines()
                boot_param[0] = boot_param[0].strip()
                if boot_param[0] == "default":
                    self.__boot_order = "c"
                elif boot_param[0] == "pxe":
                    self.__boot_order = "n"
                elif boot_param[0] == "cdrom":
                    self.__boot_order = "d"
                else:
                    self.__boot_order = "ncd"
                boot_param.append("order={}".format(self.__boot_order))
            else:
                boot_param.append("order={}".format(self.__boot_order))
        if self.__boot_menu:
            boot_param.append("menu={}".format(self.__boot_menu))
        if self.__boot_splash_name:
            boot_param.append("splash={}".format(self.__boot_splash_name))
        if self.__boot_splash_time:
            boot_param.append("splash-time={}".format(self.__boot_splash_time))
        tmp = ","
        self.add_option("-boot {}".format(tmp.join(boot_param)))

        machine_option = "-machine q35,usb=off,vmport=off"
        if self.__iommu:
            machine_option = ",".join([machine_option, "iommu=on"])
        self.add_option(machine_option)

        if self.__cdrom_file:
            self.add_option("-cdrom {}".format(self.__cdrom_file))

        if self.__socket_serial and self.__sol_enabled:
            chardev = CCharDev({
                "backend": "socket",
                "path": self.__socket_serial,
                "wait": "off"
            })
            chardev.logger = self.logger
            chardev.set_id("serial0")
            chardev.init()
            chardev.handle_parms()

            self.add_option(chardev.get_option())
            self.add_option("-device isa-serial,chardev={}".format(chardev.get_id()))

        self.add_option("-uuid {}".format(str(uuid.uuid4())))

        if self.__kernel and self.__initrd:
            self.add_option("-kernel {} -initrd {}".format(self.__kernel, self.__initrd))

        if self.__cmdline:
            self.add_option("--append \"{}\"".format(self.__cmdline))

        for element_obj in self.__element_list:
            element_obj.handle_parms()

    # override Task.terminate, use monitor to shutdown qemu
    def terminate(self):
        if self.__force_shutdown:
            super(CCompute, self).terminate()
            return

        if self._task_is_running():
            self.__monitor.open()
            if self.__monitor.get_mode() == "readline":
                self.__monitor.send("system_powerdown\n")
            elif self.__monitor.get_mode() == "control":
                self.__monitor.send({"execute": "system_powerdown"})
            self.__monitor.close()

        start = time.time()
        while time.time() - start < 2 * 60:
            if not self._task_is_running():
                if os.path.exists(self.get_pid_file()):
                    os.remove(self.get_pid_file())
                break
            time.sleep(1)
        else:
            super(CCompute, self).terminate()

class CBMC(Task):

    VBMC_TEMP_CONF = os.path.join(config.infrasim_template, "vbmc.conf")

    def __init__(self, bmc_info={}):
        super(CBMC, self).__init__()

        self.__bmc = bmc_info
        self.__address = None
        self.__channel = None
        self.__lan_interface = None
        self.__lancontrol_script = ""
        self.__chassiscontrol_script = ""
        self.__startcmd_script = ""
        self.__startnow = "true"
        self.__poweroff_wait = None
        self.__kill_wait = None
        self.__username = None
        self.__password = None
        self.__emu_file = None
        self.__config_file = ""
        self.__bin = "ipmi_sim"
        self.__port_iol = None
        self.__ipmi_listen_range = "::"
        self.__intf_not_exists = False
        self.__intf_no_ip = False

        # Be careful with updating this number, it could cause FRU index confliction
        # on particular platform, e.g. onr FRU of s2600wtt already occupied index 10
        self.__historyfru = 99

        # Node wise attributes
        self.__vendor_type = None
        self.__port_ipmi_console = 9000
        self.__port_qemu_ipmi = 9002
        self.__sol_device = ""
        self.__sol_enabled = True
        self.__node_name = None

    def enable_sol(self, enabled):
        self.__sol_enabled = enabled

    def set_type(self, vendor_type):
        self.__vendor_type = vendor_type

    def set_port_ipmi_console(self, port):
        self.__port_ipmi_console = port

    def set_port_qemu_ipmi(self, port):
        self.__port_qemu_ipmi = port

    def set_sol_device(self, device):
        self.__sol_device = device

    def get_config_file(self):
        return self.__config_file

    def set_config_file(self, dst):
        self.__config_file = dst

    def get_emu_file(self):
        return self.__emu_file

    def set_emu_file(self, path):
        self.__emu_file = path

    def set_node_name(self, node_name):
        self.__node_name = node_name

    @run_in_namespace
    def precheck(self):
        # check if ipmi_sim exists
        try:
            run_command("which {}".format(self.__bin))
        except CommandRunFailed:
            self.logger.exception("[BMC] Cannot find {}".format(self.__bin))
            raise CommandNotFound(self.__bin)

        # check script exits
        if not os.path.exists(self.__lancontrol_script):
            self.logger.exception("[BMC] Lan control script {} doesn\'t exist".
                                  format(self.__lancontrol_script))
            raise ArgsNotCorrect("Lan control script {} doesn\'t exist".
                                 format(self.__lancontrol_script))

        if not os.path.exists(self.__chassiscontrol_script):
            self.logger.exception("[BMC] Chassis control script {} doesn\'t exist".
                                  format(self.__chassiscontrol_script))
            raise ArgsNotCorrect("Chassis control script {} doesn\'t exist".
                                 format(self.__chassiscontrol_script))

        if not os.path.exists(self.__startcmd_script):
            self.logger.exception("[BMC] startcmd script {} desn\'t exist".
                                  format(self.__startcmd_script))
            raise ArgsNotCorrect("startcmd script {} doesn\'t exist".
                                 format(self.__startcmd_script))

        # check if self.__port_qemu_ipmi in use
        if helper.check_if_port_in_use("0.0.0.0", self.__port_qemu_ipmi):
            self.logger.exception("[BMC] Port {} is already in use.".
                                  format(self.__port_qemu_ipmi))
            raise ArgsNotCorrect("Port {} is already in use.".format(self.__port_qemu_ipmi))

        if helper.check_if_port_in_use("0.0.0.0", self.__port_ipmi_console):
            self.logger.exception("[BMC] Port {} is already in use.".
                                  format(self.__port_ipmi_console))
            raise ArgsNotCorrect("Port {} is already in use.".format(self.__port_ipmi_console))

        # check lan interface exists
        if self.__lan_interface not in helper.get_all_interfaces():
            print "Specified BMC interface {} doesn\'t exist, but BMC will still start."\
                .format(self.__lan_interface)
            self.logger.warning("[BMC] Specified BMC interface {} doesn\'t exist.".
                                format(self.__lan_interface))

        # check if lan interface has IP address
        elif not self.__ipmi_listen_range:
            print "No IP is found on interface {}, but BMC will still start.".format(self.__lan_interface)
            self.logger.warning("[BMC] No IP is found on BMC interface {}.".
                                format(self.__lan_interface))

        # check attribute
        if self.__poweroff_wait < 0:
            self.logger.exception("[BMC] poweroff_wait is expected to be >= 0, "
                                  "it's set to {} now".
                                  format(self.__poweroff_wait))
            raise ArgsNotCorrect("poweroff_wait is expected to be >= 0, "
                                 "it's set to {} now".
                                 format(self.__poweroff_wait))

        if type(self.__poweroff_wait) is not int:
            self.logger.exception("[BMC] poweroff_wait is expected to be integer, "
                                  "it's set to {} now".
                                  format(self.__poweroff_wait))
            raise ArgsNotCorrect("poweroff_wait is expected to be integer, "
                                 "it's set to {} now".
                                 format(self.__poweroff_wait))

        if self.__kill_wait < 0:
            self.logger.exception("[BMC] kill_wait is expected to be >= 0, "
                                  "it's set to {} now".
                                  format(self.__kill_wait))
            raise ArgsNotCorrect("kill_wait is expected to be >= 0, "
                                 "it's set to {} now".
                                 format(self.__kill_wait))

        if type(self.__kill_wait) is not int:
            self.logger.exception("[BMC] kill_wait is expected to be integer, "
                                  "it's set to {} now".
                                  format(self.__kill_wait))
            raise ArgsNotCorrect("kill_wait is expected to be integer, "
                                 "it's set to {} now".
                                 format(self.__kill_wait))

        if self.__port_iol < 0:
            self.logger.exception("[BMC] Port for IOL(IPMI over LAN) is expected "
                                  "to be integer, it's set to {} now".
                                  format(self.__port_iol))
            raise ArgsNotCorrect("Port for IOL(IPMI over LAN) is expected "
                                 "to be >= 0, it's set to {} now".
                                 format(self.__port_iol))

        if type(self.__port_iol) is not int:
            self.logger.exception("[BMC] Port for IOL(IPMI over LAN) is expected "
                                  "to be integer, it's set to {} now".
                                  format(self.__port_iol))
            raise ArgsNotCorrect("Port for IOL(IPMI over LAN) is expected "
                                 "to be integer, it's set to {} now".
                                 format(self.__port_iol))

        if self.__historyfru < 0:
            self.logger.exception("[BMC] History FRU is expected to be >= 0, "
                                  "it's set to {} now".
                                  format(self.__historyfru))
            raise ArgsNotCorrect("History FRU is expected to be >= 0, "
                                 "it's set to {} now".
                                 format(self.__historyfru))

        if type(self.__historyfru) is not int:
            self.logger.exception("[BMC] History FRU is expected to be integer, "
                                  "it's set to {} now".
                                  format(self.__historyfru))
            raise ArgsNotCorrect("History FRU is expected to be integer, "
                                 "it's set to {} now".
                                 format(self.__historyfru))

        # check configuration file exists
        if not os.path.isfile(self.__emu_file):
            self.logger.exception("[BMC] Target emulation file does not exist: {}".
                                  format(self.__emu_file))
            raise ArgsNotCorrect("Target emulation file doesn't exist: {}".
                                 format(self.__emu_file))

        if not os.path.isfile(self.__config_file):
            self.logger.exception("[BMC] Target config file does not exist: {}".
                                  format(self.__config_file))
            raise ArgsNotCorrect("Target config file doesn't exist: {}".
                                 format(self.__config_file))

    def __render_template(self):
        for target in ["startcmd", "stopcmd", "resetcmd"]:
            if not has_option(self.__bmc, target):
                src = os.path.join(config.infrasim_template, target)
                dst = os.path.join(self.get_workspace(), "script", target)
                with open(src, "r")as f:
                    src_text = f.read()
                template = jinja2.Template(src_text)
                dst_text = template.render(
                    yml_file=os.path.join(self.get_workspace(),
                                          "etc/infrasim.yml")
                )
                with open(dst, "w") as f:
                    f.write(dst_text)
                os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        if not has_option(self.__bmc, "startcmd"):
            self.__startcmd_script = os.path.join(self.get_workspace(),
                                                  "script", "startcmd")

        if not has_option(self.__bmc, "chassiscontrol"):
            path_startcmd = os.path.join(self.get_workspace(),
                                         "script/startcmd")
            path_stopcmd = os.path.join(self.get_workspace(),
                                        "script/stopcmd")
            path_resetcmd = os.path.join(self.get_workspace(),
                                         "script/resetcmd")
            path_bootdev = os.path.join(self.get_workspace(), "bootdev")
            path_qemu_pid = os.path.join(self.get_workspace(),
                                         ".{}-node.pid".format(self.__node_name))
            src = os.path.join(config.infrasim_template, "chassiscontrol")
            dst = os.path.join(self.get_workspace(),
                               "script/chassiscontrol")
            with open(src, "r") as f:
                src_text = f.read()
            template = jinja2.Template(src_text)
            dst_text = template.render(startcmd=path_startcmd,
                                       stopcmd=path_stopcmd,
                                       resetcmd=path_resetcmd,
                                       qemu_pid_file=path_qemu_pid,
                                       bootdev=path_bootdev)
            with open(dst, "w") as f:
                f.write(dst_text)
            os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            self.__chassiscontrol_script = dst

        if not has_option(self.__bmc, "lancontrol"):
            shutil.copy(os.path.join(config.infrasim_template, "lancontrol"),
                        os.path.join(self.get_workspace(),
                                     "script", "lancontrol"))

            self.__lancontrol_script = os.path.join(self.get_workspace(),
                                                    "script", "lancontrol")

    def write_bmc_config(self, dst=None):
        if dst is None:
            dst = self.__config_file
        else:
            self.__config_file = dst

        # Render vbmc.conf
        bmc_conf = ""
        with open(self.__class__.VBMC_TEMP_CONF, "r") as f:
            bmc_conf = f.read()
        template = jinja2.Template(bmc_conf)
        bmc_conf = template.render(startcmd_script=self.__startcmd_script,
                                   lan_channel=self.__channel,
                                   chassis_control_script=self.__chassiscontrol_script,
                                   lan_control_script=self.__lancontrol_script,
                                   intf_not_exists=self.__intf_not_exists,
                                   intf_no_ip=self.__intf_no_ip,
                                   lan_interface=self.__lan_interface,
                                   ipmi_listen_range=self.__ipmi_listen_range,
                                   username=self.__username,
                                   password=self.__password,
                                   port_qemu_ipmi=self.__port_qemu_ipmi,
                                   port_ipmi_console=self.__port_ipmi_console,
                                   port_iol=self.__port_iol,
                                   sol_device=self.__sol_device,
                                   poweroff_wait=self.__poweroff_wait,
                                   kill_wait=self.__kill_wait,
                                   startnow=self.__startnow,
                                   historyfru=self.__historyfru,
                                   sol_enabled=self.__sol_enabled)

        with open(dst, "w") as f:
            f.write(bmc_conf)

    @run_in_namespace
    def init(self):
        self.__address = self.__bmc.get('address', 0x20)
        self.__channel = self.__bmc.get('channel', 1)

        if 'interface' in self.__bmc:
            self.__lan_interface = self.__bmc['interface']
            self.__ipmi_listen_range = helper.get_interface_ip(self.__lan_interface)
            if self.__lan_interface not in helper.get_all_interfaces():
                self.__intf_not_exists = True
            elif not self.__ipmi_listen_range:
                self.__intf_no_ip = True
        else:
            nics_list = helper.get_all_interfaces()
            self.__lan_interface = filter(lambda x: x != "lo", nics_list)[0]

        if 'lancontrol' in self.__bmc:
            self.__lancontrol_script = self.__bmc['lancontrol']
        elif self.get_workspace():
            self.__lancontrol_script = os.path.join(self.get_workspace(),
                                                    "script",
                                                    "lancontrol")
        else:
            self.__lancontrol_script = os.path.join(config.infrasim_template,
                                                    "lancontrol")

        if 'chassiscontrol' in self.__bmc:
            self.__chassiscontrol_script = self.__bmc['chassiscontrol']
        elif self.get_workspace():
            self.__chassiscontrol_script = os.path.join(self.get_workspace(),
                                                        "script",
                                                        "chassiscontrol")

        if 'startcmd' in self.__bmc:
            self.__startcmd_script = self.__bmc['startcmd']
        elif self.get_workspace():
            self.__startcmd_script = os.path.join(self.get_workspace(),
                                                  "script",
                                                  "startcmd")

        if self.__bmc.get("startnow") is False:
            self.__startnow = "false"

        self.__poweroff_wait = self.__bmc.get('poweroff_wait', 5)
        self.__kill_wait = self.__bmc.get('kill_wait', 1)
        self.__username = self.__bmc.get('username', "admin")
        self.__password = self.__bmc.get('password', "admin")
        self.__port_iol = self.__bmc.get('ipmi_over_lan_port', 623)
        self.__historyfru = self.__bmc.get('historyfru', 99)

        if 'emu_file' in self.__bmc:
            self.__emu_file = self.__bmc['emu_file']
        elif self.get_workspace():
            self.__emu_file = os.path.join(self.get_workspace(),
                                           "data/{}.emu".format(self.__vendor_type))
        else:
            self.__emu_file = os.path.join(config.infrasim_data,
                                           "{0}/{0}.emu".format(self.__vendor_type))

        if self.__sol_device:
            pass
        elif self.get_workspace():
            self.__sol_device = os.path.join(self.get_workspace(), ".pty0")
        else:
            self.__sol_device = os.path.join(config.infrasim_etc, "pty0")

        if 'config_file' in self.__bmc:
            self.__config_file = self.__bmc['config_file']
            if os.path.exists(self.__config_file):
                shutil.copy(self.__config_file,
                            os.path.join(self.get_workspace(), "etc/vbmc.conf"))
        elif self.get_workspace() and not self._task_is_running():
            # render template
            self.__render_template()
            self.write_bmc_config(os.path.join(self.get_workspace(), "etc/vbmc.conf"))
        elif os.path.exists(os.path.join(self.get_workspace(), "etc/vbmc.conf")):
            self.__config_file = os.path.join(self.get_workspace(), "etc/vbmc.conf")
        else:
            self.logger.exception("[BMC] Can not find vbmc.conf")
            raise Exception("Couldn't find vbmc.conf!")

    def get_commandline(self):
        path = os.path.join(self.get_workspace(), "data")
        ipmi_cmd_str = "{0} -c {1} -f {2} -n -s {3}" .\
            format(self.__bin, self.__config_file, self.__emu_file, path)

        return ipmi_cmd_str


class CSocat(Task):
    def __init__(self):
        super(CSocat, self).__init__()

        self.__bin = "socat"

        # Node wise attributes
        self.__socket_serial = ""
        self.__sol_device = ""

    def set_socket_serial(self, o):
        self.__socket_serial = o

    def set_sol_device(self, device):
        self.__sol_device = device

    def precheck(self):

        # check if socat exists
        try:
            code, socat_cmd = run_command("which socat")
            self.__bin = socat_cmd.strip(os.linesep)
        except CommandRunFailed:
            self.logger.exception("[Socat] Can't find file socat")
            raise CommandNotFound("socat")

        if not self.__sol_device:
            self.logger.exception("[Socat] No SOL device is defined")
            raise ArgsNotCorrect("No SOL device is defined")

        if not self.__socket_serial:
            self.logger.exception("[Socat] No socket file for serial is defined")
            raise ArgsNotCorrect("No socket file for serial is defined")

    def init(self):
        if self.__sol_device:
            pass
        elif self.get_workspace():
            self.__sol_device = os.path.join(self.get_workspace(), ".pty0")
        else:
            self.__sol_device = os.path.join(config.infrasim_etc, "pty0")

        if self.__socket_serial:
            pass
        elif self.get_workspace():
            self.__socket_serial = os.path.join(self.get_workspace(), ".serial")
        else:
            self.__socket_serial = os.path.join(config.infrasim_etc, "serial")

    def terminate(self):
        super(CSocat, self).terminate()
        if os.path.exists(self.__socket_serial):
            os.remove(self.__socket_serial)

    def get_commandline(self):
        socat_str = "{0} pty,link={1},waitslave " \
            "unix-listen:{2},fork".\
            format(self.__bin, self.__sol_device, self.__socket_serial)

        return socat_str


class CRacadm(Task):
    def __init__(self, racadm_info):
        super(CRacadm, self).__init__()

        self.__bin = "racadmsim"

        self.__racadm_info = racadm_info

        self.__node_name = "default"
        self.__port_idrac = 10022
        self.__username = ""
        self.__password = ""
        self.__interface = None
        self.__ip = ""
        self.__data_src = ""

    def precheck(self):
        if not self.__ip:
            self.logger.exception("[Racadm] Specified racadm interface {} "
                                  "doesn\'t exist".
                                  format(self.__interface))
            raise ArgsNotCorrect("Specified racadm interface {} doesn\'t exist".
                                 format(self.__interface))

        if helper.check_if_port_in_use(self.__ip, self.__port_idrac):
            self.logger.exception("[Racadm] Racadm port {}:{} is already in use.".
                                  format(self.__ip,
                                         self.__port_idrac))
            raise ArgsNotCorrect("Racadm port {}:{} is already in use.".
                                 format(self.__ip,
                                        self.__port_idrac))

    @run_in_namespace
    def init(self):
        if "interface" in self.__racadm_info:
            self.__interface = self.__racadm_info.get("interface", "")
            self.__ip = helper.get_interface_ip(self.__interface)
        else:
            self.__ip = "0.0.0.0"
        self.__port_idrac = self.__racadm_info.get("port", 10022)
        self.__username = self.__racadm_info.get("username", "admin")
        self.__password = self.__racadm_info.get("password", "admin")
        self.__data_src = self.__racadm_info.get("data", "auto")

    def set_node_name(self, name):
        self.__node_name = name

    def get_commandline(self):
        racadmsim_str = "{} {} {} {} {} {} {}".\
            format(self.__bin,
                   self.__node_name,
                   self.__ip,
                   self.__port_idrac,
                   self.__username,
                   self.__password,
                   self.__data_src)
        return racadmsim_str


class CNode(object):
    def __init__(self, node_info=None):
        self.__tasks_list = []
        self.__node = node_info
        self.__node_name = ""
        self.workspace = None
        self.__sol_enabled = None
        self.__netns = None
        self.__logger = infrasim_log.get_logger(LoggerType.model.value)

    @property
    def netns(self):
        return self.__netns

    def get_task_list(self):
        return self.__tasks_list

    def get_node_name(self):
        return self.__node_name

    def set_node_name(self, name):
        self.__node_name = name

    def get_node_info(self):
        return self.__node

    @run_in_namespace
    def precheck(self):
        if self.__is_running():
            return

        for task in self.__tasks_list:
            try:
                task.precheck()
            except ArgsNotCorrect as e:
                self.__logger.exception("[Node] {}".format(e.value))
                raise e

    def terminate_workspace(self):
        if Workspace.check_workspace_exists(self.__node_name):
            shutil.rmtree(self.workspace.get_workspace())
        self.__logger.info("[Node] Node {} runtime workspcace is destroyed".
                           format(self.__node_name))
        print "Node {} runtime workspace is destroyed.".format(self.__node_name)

    def init(self):
        """
        1. Prepare CNode attributes:
            - self.__node
        2. Then use this information to init workspace
        3. Use this information to init sub module
        """
        if 'name' in self.__node:
            self.set_node_name(self.__node['name'])
        else:
            self.__logger.exception("[Node] No node name is "
                                    "given in node information")
            raise ArgsNotCorrect("No node name is given in node information.")

        self.__logger = infrasim_log.get_logger(LoggerType.model.value,
                                                self.__node_name)

        if self.__node['compute'] is None:
            self.__logger.exception("[Node] No compute information")
            raise Exception("No compute information")

        if 'sol_enable' not in self.__node:
            self.__node['sol_enable'] = True
        self.__sol_enabled = self.__node['sol_enable']

        self.__netns = self.__node.get("namespace")

        # If user specify "network_mode" as "bridge" but without MAC
        # address, generate one for this network.
        for network in self.__node['compute']['networks']:
            if 'mac' not in network:
                uuid_val = uuid.uuid4()
                str1 = str(uuid_val)[-2:]
                str2 = str(uuid_val)[-4:-2]
                str3 = str(uuid_val)[-6:-4]
                network['mac'] = ":".join(["52:54:BE", str1, str2, str3])

        if self.__sol_enabled:
            socat_obj = CSocat()
            socat_obj.logger = self.__logger
            socat_obj.set_priority(0)
            socat_obj.set_task_name("{}-socat".format(self.__node_name))
            self.__tasks_list.append(socat_obj)

        bmc_info = self.__node.get('bmc', {})
        bmc_obj = CBMC(bmc_info)
        bmc_obj.logger = self.__logger
        bmc_obj.set_priority(1)
        bmc_obj.set_task_name("{}-bmc".format(self.__node_name))
        bmc_obj.enable_sol(self.__sol_enabled)
        bmc_obj.set_log_path("/var/log/infrasim/{}/openipmi.log".
                             format(self.__node_name))
        bmc_obj.set_node_name(self.__node['name'])
        self.__tasks_list.append(bmc_obj)

        compute_obj = CCompute(self.__node['compute'])
        compute_obj.logger = self.__logger
        asyncr = bmc_info.get("startnow", True)
        compute_obj.set_asyncronous(asyncr)
        compute_obj.enable_sol(self.__sol_enabled)
        compute_obj.set_priority(2)
        compute_obj.set_task_name("{}-node".format(self.__node_name))
        compute_obj.set_log_path("/var/log/infrasim/{}/qemu.log".
                                 format(self.__node_name))
        self.__tasks_list.append(compute_obj)

        if "type" in self.__node and "dell" in self.__node["type"]:
            racadm_info = self.__node.get("racadm", {})
            racadm_obj = CRacadm(racadm_info)
            racadm_obj.logger = self.__logger
            racadm_obj.set_priority(3)
            racadm_obj.set_node_name(self.__node_name)
            racadm_obj.set_task_name("{}-racadm".format(self.__node_name))
            racadm_obj.set_log_path("/var/log/infrasim/{}/racadm.log".
                                    format(self.__node_name))
            self.__tasks_list.append(racadm_obj)

        # Set interface
        if "type" not in self.__node:
            self.__logger.exception("[Node] Can't get infrasim type")
            raise ArgsNotCorrect("Can't get infrasim type")
        else:
            bmc_obj.set_type(self.__node['type'])
            compute_obj.set_type(self.__node['type'])

        if self.__sol_enabled:
            if "sol_device" in self.__node:
                socat_obj.set_sol_device(self.__node["sol_device"])
                bmc_obj.set_sol_device(self.__node["sol_device"])

            if "serial_socket" not in self.__node:
                self.__node["serial_socket"] = os.path.join(config.infrasim_home,
                                                            self.__node["name"],
                                                            ".serial")
            socat_obj.set_socket_serial(self.__node["serial_socket"])
            compute_obj.set_socket_serial(self.__node["serial_socket"])

        if "ipmi_console_port" in self.__node:
            bmc_obj.set_port_ipmi_console(self.__node["ipmi_console_port"])
            # ipmi-console shall connect to same port with the same conf file

        if "bmc_connection_port" in self.__node:
            bmc_obj.set_port_qemu_ipmi(self.__node["bmc_connection_port"])
            compute_obj.set_port_qemu_ipmi(self.__node["bmc_connection_port"])

        self.workspace = Workspace(self.__node)

        for task in self.__tasks_list:
            task.set_workspace(self.workspace.get_workspace())

        if not self.__is_running():
            self.workspace.init()

        if self.__netns:
            for task in self.__tasks_list:
                task.netns = self.__netns

        try:
            for task in self.__tasks_list:
                task.init()
        except Exception, e:
            self.__logger.exception("[Node] {}".format(str(e)))
            raise e

    # Run tasks list as the priority
    def start(self):
        # sort the tasks as the priority
        self.__tasks_list.sort(key=lambda x: x.get_priority(), reverse=False)

        for task in self.__tasks_list:
            task.run()

    def stop(self):
        # sort the tasks as the priority in reversed sequence
        self.__tasks_list.sort(key=lambda x: x.get_priority(), reverse=True)

        for task in self.__tasks_list:
            task.terminate()

    def status(self):
        for task in self.__tasks_list:
            task.status()

    def __is_running(self):
        state = False
        for task in self.__tasks_list:
            state |= task._task_is_running()

        return state


class NumaCtl(object):
    HT_FACTOR = -1

    def __init__(self):
        """
        Build core map by reading /proc/cpuinfo
        """
        self._socket_list = []
        self._core_list = []
        self._core_map = {}
        self._core_map_avai = {}

        with open("/proc/cpuinfo", "r") as fp:
            lines = fp.readlines()

        core_block = []
        core_info = {}

        for line in lines:
            if len(line.strip()) != 0:
                key, value = line.split(":", 1)
                core_info[key.strip()] = value.strip()
            else:
                core_block.append(core_info)
                core_info = {}

        for core in core_block:
            for field in ["processor", "core id", "physical id"]:
                if field not in core:
                    err = "Error getting '%s' value from /proc/cpuinfo".format(field)
                    logger_model.exception(err)
                    raise Exception(err)
                core[field] = int(core[field])

            if core["core id"] not in self._core_list:
                self._core_list.append(core["core id"])
            if core["physical id"] not in self._socket_list:
                self._socket_list.append(core["physical id"])
            key = (core["physical id"], core["core id"])
            if key not in self._core_map:
                self._core_map[key] = []
                self._core_map_avai[key] = []
            self._core_map[key].append(core["processor"])

            # Reserve first two core of each socket for system
            if key[1] in [0, 1]:
                self._core_map_avai[key].append(False)
            else:
                self._core_map_avai[key].append(True)

        self.__class__.HT_FACTOR = len(self._core_map[(0, 0)])

    def get_cpu_list(self, num):
        processor_use_up = True
        cpu_list = []
        assigned_count = 0
        socket_to_use = -1

        # Find available socket (with enough processor) to bind
        for socket in self._socket_list:
            count_avai = 0
            for core in self._core_list:
                for avai in self._core_map_avai[(socket, core)]:
                    if avai:
                        count_avai += 1
            if count_avai < num:
                continue
            else:
                socket_to_use = socket
                processor_use_up = False
                break
        if processor_use_up or socket_to_use < 0:
            logger_model.exception("All sockets don't have enough processor to bind.")
            raise Exception("All sockets don't have enough processor to bind.")

        # Append core which all HT processor are available
        for core in self._core_list:
            if num - assigned_count >= self.HT_FACTOR:
                # check if all processor are available on this core
                all_avai = reduce(lambda x, y: x and y,
                                  self._core_map_avai[(socket_to_use, core)])
                if all_avai:
                    cpu_list += self._core_map[(socket_to_use, core)]
                    self._core_map_avai[(socket_to_use, core)] = [False] * self.HT_FACTOR
                    assigned_count += self.HT_FACTOR
                    if num == assigned_count:
                        return cpu_list
            else:
                break

        # Use scattered core
        for core in self._core_list:
            # check availability of processors on this core
            core_avai_list = self._core_map_avai[(socket_to_use, core)]
            core_avai_count = len(filter(lambda x: x, core_avai_list))

            if num - assigned_count <= core_avai_count:
                # assign
                for i in range(self.HT_FACTOR):
                    if core_avai_list[i]:
                        cpu_list.append(self._core_map[(socket_to_use, core)][i])
                        self._core_map_avai[(socket_to_use, core)][i] = False
                        assigned_count += 1
                        if num == assigned_count:
                            return cpu_list

    def print_core_map(self):
        print "============================================================"
        print "Core and Socket Information (as reported by '/proc/cpuinfo')"
        print "============================================================\n"
        print "cores = ", self._core_list
        print "sockets = ", self._socket_list
        print ""

        max_processor_len = len(str(len(self._core_list) * len(self._socket_list) * self.HT_FACTOR - 1))
        max_core_map_len = max_processor_len * self.HT_FACTOR \
            + len('[, ]') + len('Socket ')
        max_core_id_len = len(str(max(self._core_list)))

        print " ".ljust(max_core_id_len + len('Core ')),
        for s in self._socket_list:
            print "Socket %s" % str(s).ljust(max_core_map_len - len('Socket ')),
        print ""
        print " ".ljust(max_core_id_len + len('Core ')),
        for s in self._socket_list:
            print "--------".ljust(max_core_map_len),
        print ""

        for c in self._core_list:
            print "Core %s" % str(c).ljust(max_core_id_len),
            for s in self._socket_list:
                print str(self._core_map[(s, c)]).ljust(max_core_map_len),
            print "\n"
