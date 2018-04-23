'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import sys
import signal
import atexit
from infrasim.log import infrasim_log
from time import sleep
import traceback
from share_memory import CShareMemory

flag_quit = False


def atexit_cb(sig=signal.SIGTERM, stack=None):
    global flag_quit
    flag_quit = True


def chassis_main(name, data_file):
    """
        Usage: chassis <chassis_name> <data_file_name>
    """
    global flag_quit
    flag_quit = False
    try:
        # register the atexit call back function
        atexit.register(atexit_cb)
        signal.signal(signal.SIGINT, atexit_cb)
        signal.signal(signal.SIGTERM, atexit_cb)
        logger = infrasim_log.get_chassis_logger(name)
        logger.info('start chassis {}'.format(name))
        memory = CShareMemory()
        key_name = "/share_mem_{}".format(name)
        with open(data_file, 'r') as fp:
            buf = fp.read()
        memory.create(key_name, len(buf))
        memory.write(0, buf)
        while not flag_quit:
            sleep(3)
        memory.close()
        logger.info('chassis {} closed'.format(name))
    except Exception as e:
        traceback.print_exc()
        logger.info('Chassis failed {}'.format(sys.exc_info()))
        sys.exit(e)
