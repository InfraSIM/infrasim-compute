'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


from infrasim import ArgsNotCorrect
from infrasim.model.core.element import CElement


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
            raise ArgsNotCorrect("[Memory] Please set memory size.")

    def init(self):
        self.__memory_size = self.__memory.get('size')

    def handle_parms(self):
        memory_option = "-m {}".format(self.__memory_size)
        self.add_option(memory_option)
