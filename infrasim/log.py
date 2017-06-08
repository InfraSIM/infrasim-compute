import logging
import logging.handlers
import os
from enum import Enum
import gzip
import shutil

infrasim_logdir = "/var/log/infrasim"
EXCEPT_LEVEL_NUM = 35


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        if self.stream:
            self.stream.close()
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    # print "%s -> %s" % (sfn, dfn)
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1.gz"
            if os.path.exists(dfn):
                os.remove(dfn)
            # These two lines below are the only new lines.
            #  I commented out the os.rename(self.baseFilename, dfn) and
            #  replaced it with these two lines.
            with open(self.baseFilename, 'rb') as f_in, \
                    gzip.open(dfn, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            # os.rename(self.baseFilename, dfn)
            # print "%s -> %s" % (self.baseFilename, dfn)
        self.mode = 'w'
        self.stream = self._open()


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
        if not os.path.exists(infrasim_logdir):
            os.mkdir(infrasim_logdir)
        for logger_name in LoggerType:
            logger = logging.getLogger("{}{}".format(
                self.__node_id, logger_name.value))
            infrasim_log_file = os.path.join(
                infrasim_logdir, "infrasim.log")
            self.__handler = logging.FileHandler(infrasim_log_file)
            formatter = logging.Formatter(
                '%(asctime)s - {} - %(filename)s:'
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
                                        'racadm.log')
            else:
                log_file = os.path.join(infrasim_logdir,
                                        self.__node_name,
                                        'runtime.log')
            logger = self.__logger_list[logger_name.value]
            handler = CompressedRotatingFileHandler(
                log_file, maxBytes=4*1024*1024, backupCount=100)
            formatter = logging.Formatter(
                '%(asctime)s - {} - %(filename)s:'
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

    def get_log_path(self, node_name):
        return os.path.join(infrasim_logdir, node_name)

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
