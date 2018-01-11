'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
from infrasim import ArgsNotCorrect
from infrasim import helper
from infrasim.model.core.element import CElement


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
            raise ArgsNotCorrect("[Chardev] Backend of chardev should be set.")

        if self.__host and not helper.is_valid_ip(self.__host):
            raise ArgsNotCorrect("[CharDev] Invalid chardev host: {}".format(self.__host))

        if self.__port:
            try:
                int(self.__port)
            except ValueError:
                raise ArgsNotCorrect("[Chardev] Port is not a valid integer: {}".format(self.__port))

            if helper.check_if_port_in_use("0.0.0.0", self.__port):
                raise ArgsNotCorrect("[Chardev] Port {} is already in use".format(self.__port))

        if self.__path:
            dir_path = os.path.dirname(self.__path)
            if not os.path.isdir(dir_path):
                raise ArgsNotCorrect("[Chardev] Path folder doesn't exist: {}".format(dir_path))

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
