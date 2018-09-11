'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
from infrasim import CommandNotFound, ArgsNotCorrect, CommandRunFailed
from infrasim import config
from infrasim import run_command
from infrasim.model.core.task import Task


class CSocat(Task):
    def __init__(self):
        super(CSocat, self).__init__()

        self.__bin = "socat"

        # Node wise attributes
        self.__socket_serial = ""
        self.__sol_device = ""
        self.__node_name = None

    def set_socket_serial(self, o):
        self.__socket_serial = o

    def set_sol_device(self, device):
        self.__sol_device = device

    def set_node_name(self, o):
        self.__node_name = o

    def precheck(self):

        # check if socat exists
        try:
            code, socat_cmd = run_command("which socat")
            self.__bin = socat_cmd.strip(os.linesep)
        except CommandRunFailed:
            self.logger.exception("[Socat] Can't find file socat")
            raise CommandNotFound("socat")

        if not self.__sol_device:
            raise ArgsNotCorrect("[Socat] No SOL device is defined")

        if not self.__socket_serial:
            raise ArgsNotCorrect("[Socat] No socket file for serial is defined")

    def init(self):
        if self.__sol_device:
            pass
        elif self.get_workspace():
            self.__sol_device = os.path.join(self.get_workspace(), ".pty0_{}".format(self.__node_name))
        else:
            self.__sol_device = os.path.join(config.infrasim_etc, "pty0_{}".format(self.__node_name))

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
