'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
import socket
import json
from telnetlib import Telnet
from infrasim import ArgsNotCorrect
from infrasim import config
from infrasim.model.core.element import CElement
from infrasim.model.elements.chardev import CCharDev


class CQemuMonitor(CElement):
    def __init__(self, monitor_info):
        super(CQemuMonitor, self).__init__()
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
            raise e

        # Monitor specific chardev attribution
        if self.__monitor["chardev"]["backend"] != "socket":
            raise ArgsNotCorrect("Invalid monitor chardev backend: {}".format(
                self.__monitor["chardev"]["backend"]))
        if self.__monitor["chardev"]["server"] is not True:
            raise ArgsNotCorrect("Invalid monitor chardev server: {}".format(
                self.__monitor["chardev"]["server"]))
        if self.__monitor["chardev"]["wait"] is not False:
            raise ArgsNotCorrect("Invalid monitor chardev wait: {}".format(
                self.__monitor["chardev"]["wait"]))

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

            self.recv()
            # enable qmp capabilities
            qmp_payload = {
                "execute": "qmp_capabilities"
            }
            self.send(qmp_payload)
            self.recv()
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

    def recv(self):
        if self.__mode == "control":
            rsp = ""
            while 1:
                snip = self.__monitor_handle.recv(1024)
                rsp += snip
                if len(snip) < 1024:
                    break
            return json.loads(rsp)
        else:
            return self.__monitor_handle.read_eager()

    def close(self):
        if self.__monitor_handle:
            self.__monitor_handle.close()
            self.logger.info("[Monitor] monitor closed.")
