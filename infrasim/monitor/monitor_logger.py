from infrasim.log import infrasim_log, LoggerType

mlog = infrasim_log.get_logger(logger_name=LoggerType.monitor.value, node_name=None)


def init_logger(node_name):
    mlog = infrasim_log.get_logger(logger_name=LoggerType.monitor.value, node_name=node_name)
    return mlog


def get_logger():
    return mlog
