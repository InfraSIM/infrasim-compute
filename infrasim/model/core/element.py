'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


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


from infrasim.log import infrasim_log, LoggerType


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
