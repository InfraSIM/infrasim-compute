import logging
import os
from enum import Enum


infrasim_logdir = "/var/log/infrasim"
infrasim_log_file = '/var/log/infrasim.log'
EXCEPT_LEVEL_NUM = 35


def EXCEPTION(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(EXCEPT_LEVEL_NUM, message, args, **kws)

# add EXCEPTION level
logging.Logger.exception = EXCEPTION
logging.addLevelName(EXCEPT_LEVEL_NUM, "EXCEPTION")


class LoggerType(Enum):
    model = 'Model'
    qemu = 'Qemu'
    ipmi_sim = 'Ipmi_sim'
    socat = 'Socat'
    ipmi_console = 'Ipmi-console'
    racadm = 'Racadmsim'
    cmd = 'Cmd'
    config = 'Config'
    environment = 'Environment'


class LoggerList(object):

    # set "infrasim.log" as all default logger files
    def __init__(self, node_id):
        self.__logger_list = {}
        self.__node_name = None
        self.__node_id = node_id
        for logger_name in LoggerType:
            logger = logging.getLogger("{}{}".format(self.__node_id, logger_name.value))
            self.__handler = logging.FileHandler(infrasim_log_file)
            formatter = logging.Formatter('%(asctime)s - {} - %(filename)s:'
                                          '%(lineno)s - %(levelname)s - %(message)s'.
                                          format(logger_name.value))
            self.__handler.setFormatter(formatter)
            logger.addHandler(self.__handler)
            logger.setLevel(logging.DEBUG)
            self.__logger_list[logger_name.value] = logger

    # if logger_name is not given, raise Exception
    # if logger_name is 'Cmd', the log file is 'infrasim.log'
    # if node_name is not given, the default log file is 'infrasim.log'
    # if node_name is given, the default log depends on the logger_name as follows:
    #    'Config': /infrasim/<node_name>/static.log
    #    'Model', 'Qemu': /infrasim/<node_name>/runtime.log
    #    'Ipmi-console': /infrasim/<node_name>/ipmi-console.log
    def init(self, node_name=None):
        if node_name is None:
            return
        if self.__node_name is not None:
            return
        self.__node_name = node_name
        if not os.path.exists(infrasim_logdir):
            os.mkdir(infrasim_logdir)
        log_base = os.path.join(infrasim_logdir, self.__node_name)
        if not os.path.exists(log_base):
            os.mkdir(log_base)
        for logger_name in LoggerType:
            log_file = ''
            if logger_name is LoggerType.cmd:
                continue
            elif logger_name is LoggerType.config:
                log_file = os.path.join(infrasim_logdir,
                                        self.__node_name,
                                        'static.log')
            elif logger_name is LoggerType.ipmi_console:
                log_file = os.path.join(infrasim_logdir,
                                        self.__node_name,
                                        'ipmi-console.log')
            elif logger_name is LoggerType.racadm:
                log_file = os.path.join(infrasim_logdir,
                                        self.__node_name,
                                        'racadmsim.log')
            else:
                log_file = os.path.join(infrasim_logdir,
                                        self.__node_name,
                                        'runtime.log')
            logger = self.__logger_list[logger_name.value]
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - {} - %(filename)s:'
                                          '%(lineno)s - %(levelname)s - %(message)s'
                                          .format(logger_name.value))
            handler.setFormatter(formatter)
            logger.handlers = []
            logger.addHandler(handler)
            self.__logger_list[logger_name.value] = logger

    def get_node_id(self):
        return self.__node_id

    def get_logger(self, logger_name):
        try:
            logger = self.__logger_list[logger_name]
        except KeyError as e:
            raise e
        return logger

    def del_logger_list(self):
        for logger in self.__logger_list.values():
            logger.handlers = []


class InfrasimLog(object):
    def __init__(self):
        self.__node_list = {}
        self.__default = LoggerList(0)

    def add_node(self, node_name):
        node_id_list = []
        for node in self.__node_list.values():
            node_id_list.append(node.get_node_id())
        node_id_list.sort()
        node_id = 1
        for id in node_id_list:
            if id is not node_id:
                break
            else:
                node_id += 1
        node_logger = LoggerList(node_id)
        node_logger.init(node_name)
        self.__node_list[node_name] = node_logger

    def remove_node(self, node_name):
        try:
            logger_list = self.__node_list[node_name]
            logger_list.del_logger_list()
            del self.__node_list[node_name]
        except KeyError:
            pass

    def get_logger(self, logger_name, node_name=None):
        if node_name is None:
            try:
                return self.__default.get_logger(logger_name)
            except KeyError as e:
                raise e
        if node_name not in self.__node_list.keys():
            self.add_node(node_name)
        logger_list = self.__node_list[node_name]
        return logger_list.get_logger(logger_name)

infrasim_log = InfrasimLog()
