'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import subprocess
import os
import time
import threading
import telnetlib
import logging
import socket
import Queue
import re
import env
import traceback
from infrasim import config
from infrasim import run_command
from infrasim.workspace import Workspace


lock = threading.Lock()

# logger
logger = logging.getLogger("ipmi-console")


# telnet to vBMC
tn = telnetlib.Telnet()

msg_queue = Queue.Queue()


class IpmiError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def init_logger(instance="default"):

    logger.setLevel(logging.ERROR)

    log_folder = os.path.join(config.infrasim_logdir, instance)
    if not os.path.exists(log_folder):
        os.mkdir(log_folder)
    log_path = os.path.join(log_folder, "ipmi-console.log")

    if os.path.isfile(log_path) is True:
        os.remove(log_path)

    # create file handler which logs even debug messages
    fh = logging.FileHandler(log_path)

    # create console handler with a higher log level
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.ERROR)
    logger.setLevel(logging.INFO)

    # create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)


def init_env(instance):
    """
    This is to sync ipmi-console with runtime vBMC configuration.
    Initial version capture infrasim instance name by infrasim-main status, while we
    have a plan to give instance name to ipmi-console so that it can be attached to
    target vBMC instance.
    """
    if not Workspace.check_workspace_exists(instance):
        raise IpmiError("Warning: there is no node {} workspace. Please start node {} first.".format(instance, instance))
    output = run_command("infrasim node status")
    if output[0] == 0 and "{}-bmc is stopped".format(instance) in output[1]:
        raise IpmiError("Warning: node {} has not started BMC. Please start node {} first.".format(instance, instance))

    logger.info("Init ipmi-console environment for infrasim instance: {}".
                format(instance))

    # Get runtime vbmc.conf
    vbmc_conf_path = os.path.join(os.environ["HOME"], ".infrasim", instance, "etc", "vbmc.conf")
    if not os.path.exists(vbmc_conf_path):
        msg = "{} vBMC configuration is not defined at {}".format(instance, vbmc_conf_path)
        logger.error(msg)
        raise Exception(msg)
    else:
        msg = "Target vbmc to attach is: {}".format(vbmc_conf_path)
        logger.info(msg)

    # Get runtime infrasim.yml
    infrasim_yml_path = os.path.join(os.environ["HOME"], ".infrasim", instance, "etc", "infrasim.yml")
    if not os.path.exists(infrasim_yml_path):
        msg = "{} infrasim instance is not defined at {}".format(instance, infrasim_yml_path)
        logger.error(msg)
        raise Exception(msg)
    else:
        msg = "Target infrasim instance to attach is: {}".format(infrasim_yml_path)
        logger.info(msg)

    # Get variable and set to ipmi-console env
    # - PORT_TELNET_TO_VBMC
    # - VBMC_IP
    # - VBMC_PORT
    with open(vbmc_conf_path, 'r') as fp:
        conf = fp.read()

        p_telnet = re.compile(r"^\s*console\s*[\d:\.]+\s+(?P<port_telnet_to_vbmc>\d+)",
                              re.MULTILINE)
        s_telnet = p_telnet.search(conf)
        if s_telnet:
            env.PORT_TELNET_TO_VBMC = int(s_telnet.group("port_telnet_to_vbmc"))
            logger.info("PORT_TELNET_TO_VBMC: {}".format(env.PORT_TELNET_TO_VBMC))
        else:
            raise Exception("PORT_TELNET_TO_VBMC is not found")

        p_vbmc = re.compile(r"^\s*addr\s*(?P<vbmc_ip>[\d:\.]+)\s*(?P<vbmc_port>\d+)",
                            re.MULTILINE)
        s_vbmc = p_vbmc.search(conf)
        if s_vbmc:
            ip = s_vbmc.group("vbmc_ip")
            if ip == "::" or ip == "0.0.0.0":
                env.VBMC_IP = "localhost"
            else:
                env.VBMC_IP = ip
            logger.info("VBMC_IP: {}".format(env.VBMC_IP))
            env.VBMC_PORT = int(s_vbmc.group("vbmc_port"))
            logger.info("VBMC_PORT: {}".format(env.VBMC_PORT))
        else:
            raise Exception("VBMC_IP and VBMC_PORT is not found")

    # Get variable and set to ipmi-console env
    # - PORT_SSH_FOR_CLIENT
    with open(infrasim_yml_path, 'r') as fp:
        conf = fp.read()

        p_port = re.compile(r"^\s*ipmi_console_ssh:\s*(?P<port_ssh_for_client>\d+)",
                            re.MULTILINE)
        s_port = p_port.search(conf)
        if s_port:
            env.PORT_SSH_FOR_CLIENT = int(s_port.group("port_ssh_for_client"))
        else:
            env.PORT_SSH_FOR_CLIENT = 9300
        logger.info("PORT_SSH_FOR_CLIENT: {}".format(env.PORT_SSH_FOR_CLIENT))


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
        tn.open('localhost', env.PORT_TELNET_TO_VBMC)
        tn.write(command)
        time.sleep(0.1)
        result = tn.read_some()
        tn.close()
        logger.info("IPMI SIM command result: " + result)
    except socket.error as se:
        logger.error("Unable to connect lanserv at {0}: {1}".
                     format(env.PORT_TELNET_TO_VBMC, se))
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
               "-I", "lan",
               "-H", env.VBMC_IP,
               "-U", vbmc_user,
               "-P", vbmc_pass,
               "-p", str(env.VBMC_PORT)]
    for cmd in cmds:
        dst_cmd.append(cmd)
    try:
        child = subprocess.Popen(dst_cmd,
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        (stdout, stderr) = child.communicate()
    except:
        logger.error(traceback.format_exc())
        raise
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
