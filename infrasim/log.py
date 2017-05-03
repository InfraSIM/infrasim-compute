import logging
import os
from infrasim.config import infrasim_log_file, infrasim_logdir

EXCEPT_LEVEL_NUM = 35


def EXCEPTION(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(EXCEPT_LEVEL_NUM, message, args, **kws)


class logger_type:
    def __init__(self):
        self.model = 'Model'
        self.qemu = 'Qemu'
        self.ipmi_sim = 'Ipmi_sim'
        self.socat = 'Socat'
        self.ipmi_console = 'Ipmi-console'
        self.racadm = 'Racadmsim'
        self.cmd = 'Cmd'
        self.config = 'Config'
        self.environment = 'Environment'


class InfrasimLog(object):
    def __init__(self):
        self.__log_list = {}
        self.__handler = None

    def init(self):
        # add EXCEPT level
        logging.Logger.exception = EXCEPTION
        logging.addLevelName(EXCEPT_LEVEL_NUM, "EXCEPTION")
        self.__handler = logging.FileHandler(infrasim_log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                      '%(filename)s:%(lineno)s - %(levelname)s - %(message)s')
        self.__handler.setFormatter(formatter)
        log_type = logger_type()
        logger_list = [log_type.cmd, log_type.model, log_type.config, log_type.qemu, log_type.ipmi_sim,
                       log_type.socat, log_type.ipmi_console, log_type.racadm, log_type.environment]

        for logger_name in logger_list:
            logger = logging.getLogger(logger_name)
            logger.addHandler(self.__handler)
            logger.setLevel(logging.DEBUG)
            self.__log_list[logger_name] = logger

    def get_logger(self, logger_name, node_name=None):
        if logger_name in self.__log_list:
            if node_name is None:
                return self.__log_list[logger_name]
            else:
                log_type = logger_type()
                log_base = os.path.join(infrasim_logdir, node_name)
                if not os.path.exists(log_base):
                    os.mkdir(log_base)
                log_file = None
                if logger_name is log_type.cmd:
                    log_file = os.path.join(infrasim_logdir, 'infrasim.log')
                elif logger_name is log_type.config:
                    log_file = os.path.join(infrasim_logdir, node_name, 'static.log')
                else:
                    log_file = os.path.join(infrasim_logdir, node_name, 'runtime.log')

                logger = self.__log_list[logger_name]
                logger.removeHandler(self.__handler)
                handler = logging.FileHandler(log_file)
                formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                              '%(filename)s:%(lineno)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                return logger
        else:
            raise Exception("can not find logger {}".format(logger_name))
