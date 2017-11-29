'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim import ArgsNotCorrect
from infrasim.model.core.element import CElement
from infrasim.model.elements.chardev import CCharDev


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
            raise ArgsNotCorrect("[IPMI] -chardev should set.")

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
