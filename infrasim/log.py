import logging

infrasim_log_file = '/var/log/infrasim.log'
EXCEPT_LEVEL_NUM = 35


def EXCEPTION(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    self._log(EXCEPT_LEVEL_NUM, message, args, **kws)


class logger_type:
    def __init__(self):
        self.cmd = 'Cmd'
        self.model = 'Model'
        self.config = 'Config'
        self.qemu = 'Qemu'
        self.ipmi_sim = 'Ipmi_sim'
        self.socat = 'Socat'
        self.ipmi_console = 'Ipmi-console'
        self.racadm = 'Racadmsim'
        self.environment = 'Environment'

class InfrasimLog(object):
    def __init__(self):
        self.__log_list = {}
        self.__log_file = None

    def init(self):
        # add EXCEPT level
        logging.Logger.exception = EXCEPTION
        logging.addLevelName(EXCEPT_LEVEL_NUM, "EXCEPTION")

        self.__log_file = infrasim_log_file
        handler = logging.FileHandler(self.__log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                      '%(filename)s:%(lineno)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        log_type = logger_type()
        logger_list = [log_type.cmd, log_type.model, log_type.config, log_type.qemu, log_type.ipmi_sim,
                       log_type.socat, log_type.ipmi_console, log_type.racadm, log_type.environment]

        for logger_name in logger_list:
            logger = logging.getLogger(logger_name)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            self.__log_list[logger_name] = logger

    def get_logger(self, logger_name):
        if logger_name in self.__log_list:
            return self.__log_list[logger_name]
        else:
            raise Exception("can not find logger {}".format(logger_name))
