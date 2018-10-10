'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import sys
import subprocess
import re
import signal
import atexit
from infrasim.log import infrasim_log
from time import sleep
import traceback
from share_memory import CShareMemory
from agent import Agent

flag_quit = False


def atexit_cb(sig=signal.SIGTERM, stack=None):
    global flag_quit
    flag_quit = True


def update_power_status(name):
    # set power status of node according to status of qemu.
    # 0xff: power is on.
    # 0x00: power if off.
    title = "chassis/nodes_power"
    agent = Agent()
    agent.open(name)
    status = agent.get(title)
    if status:
        # query status of qemu process.
        ps = subprocess.Popen("ps -f -C qemu-system-x86_64 | grep '{}_node_.*-node' -o".format(name),
                              shell=True, stdout=subprocess.PIPE)
        output = ps.stdout.read()
        ps.stdout.close()
        ps.wait()
        re_obj = re.compile("{}_node_(\d+)-node".format(name))
        result = re_obj.findall(output)
        result = map(lambda x: int(x), result)

        # update power status.
        status = ['\0'] * len(status)
        for idx in result:
            if idx < len(status):
                status[idx] = '\xff'
        agent.set(title, ''.join(status))
    agent.close()


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
            update_power_status(name)
        memory.close()
        logger.info('chassis {} closed'.format(name))
    except Exception as e:
        traceback.print_exc()
        logger.info('Chassis failed {}'.format(sys.exc_info()))
        sys.exit(e)
