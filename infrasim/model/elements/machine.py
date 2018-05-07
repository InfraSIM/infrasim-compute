'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

from infrasim.model.core.element import CElement


class CMachine(CElement):

    def __init__(self, machine_info):
        super(CMachine, self).__init__()
        self.__machine = machine_info
        self.__type = None
        self.__usb_state = None
        self.__vmport_state = None
        self.__mem_merge = None
        self.__sata = None
        self.__igd_passthru = None

    def precheck(self):
        pass

    def init(self):
        if self.__machine is None:
            self.__machine = {"type": "q35", "usb": "off", "vmport": "off"}

        self.__type = self.__machine.get("type", "q35")
        self.__usb_state = self.__machine.get("usb", "off")
        self.__vmport_state = self.__machine.get("vmport", "off")
        self.__mem_merge = self.__machine.get("mem-merge", False)
        self.__kernel_irqchip = self.__machine.get("kernel-irqchip", "off")
        self.__sata = self.__machine.get("sata", "false")
        self.__igd_passthru = self.__machine.get("igd-passthru")

    def handle_parms(self):
        machine_option = "-machine {},usb={},vmport={}".format(
            self.__type, self.__usb_state, self.__vmport_state,
        )

        if self.__mem_merge is not None:
            machine_option = ','.join([machine_option, "mem-merge={}".format(self.__mem_merge)])

        if self.__kernel_irqchip is not None:
            machine_option = ','.join([machine_option, "kernel-irqchip={}".format(self.__kernel_irqchip)])

        if self.__sata:
            machine_option = ','.join([machine_option, "sata={}".format(self.__sata)])

        if self.__igd_passthru:
            machine_option = ','.join([machine_option, "igd-passthru={}".format(self.__igd_passthru)])

        self.add_option(machine_option)
