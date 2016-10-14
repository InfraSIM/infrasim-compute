'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import subprocess
import os
import sys
import time
import threading
import telnetlib
import logging

import socket
import Queue
import re

lock = threading.Lock()

# logger
logger = logging.getLogger("ipmi_sim")
LOG_FILE = '/var/log/ipmi_sim.log'

# telnet to vBMC
tn = telnetlib.Telnet()

msg_queue = Queue.Queue()


def init_logger():
    logger.setLevel(logging.ERROR)

    if os.path.isfile(LOG_FILE) is True:
        os.remove(LOG_FILE)

    # create file handler which logs even debug messages
    fh = logging.FileHandler(LOG_FILE)

    # create console handler with a higher log level
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)


def get_logger():
    return logger


# safe check
# convert a str number to int, the base is hex
# if the id str is illegal, return None
def str_hex_to_int(str_num):
    int_num = None
    if str_num.startswith('0x'):
        str_num = str_num.lstrip('0x')

    try:
        int_num = int(str_num, 16)
    except:
        logger.exception("Not a valid entry - need a hex value")

    return int_num


# telnet to vBMC console
def open_telnet_session():
    pass


# send IPMI SIM command to the vBMC
def send_ipmi_sim_command(command):
    lock.acquire()
    logger.info("send IPMI SIM command: " + command.strip())
    result = ""
    try:
        tn.open('localhost', '9000')
        tn.write(command)
        time.sleep(0.1)
        result = tn.read_some()
        tn.close()
        logger.info("IPMI SIM command result: " + result)
    except socket.error as se:
        logger.error("Unable to connect lanserv at 9000: {0}".format(se))
    finally:
        lock.release()

    return result


# close telnet session
def close_telnet_session():
    pass


# send ipmitool command to vBMC
def send_ipmitool_command(*cmds):
    vbmc_user = "admin"
    output = send_ipmi_sim_command(
        "get_user_password 0x20 {}\n".format(vbmc_user))
    for line in output.split(os.linesep):
        pass_obj = re.search(r"(^[^>].*)", line)
        if pass_obj:
            break

    if pass_obj is None:
        return -1

    vbmc_pass = pass_obj.group().strip('\r\n')

    lock.acquire()
    dst_cmd = ["ipmitool",
               "-I", "lan", "-H", 'localhost', "-U", vbmc_user, "-P", vbmc_pass]
    for cmd in cmds:
        dst_cmd.append(cmd)
    child = subprocess.Popen(dst_cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
    (stdout, stderr) = child.communicate()
    child.wait()
    logger.info("ipmitool command: " + ' '.join(dst_cmd))
    logger.info("ipmitool command stdout: " + stdout.strip())

    if stderr != '':
        err_message = "failed to send ipmitool command: {0}".format(dst_cmd)
        logger.error(err_message)
        lock.release()
        return -1
    lock.release()
    return stdout
