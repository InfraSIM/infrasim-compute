'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import time
import config
from infrasim.model import CSocat, CNode
from infrasim.helper import yaml_load
from . import run_command, logger, CommandNotFound, CommandRunFailed, InfraSimError


def get_socat():
    try:
        code, socat_cmd = run_command("which socat")
        return socat_cmd.strip(os.linesep)
    except CommandRunFailed:
        raise CommandNotFound("/usr/bin/socat")


def status_socat():
    try:
        run_command("pidof socat")
        print "Infrasim Socat service is running"
    except CommandRunFailed:
        print "Inrasim Socat service is stopped"


def start_socat(conf_file=config.infrasim_default_config):
    try:
        with open(conf_file, 'r') as f_yml:
            conf = yaml_load(f_yml)

        node = CNode(conf)
        if "name" in conf:
            node.set_node_name(conf["name"])

        node.init()

        socat = CSocat()
        # Read SOL device, serial port from conf
        # and set to socat
        if "sol_device" in conf:
            socat.set_sol_device(conf["sol_device"])
        if "serial_socket" in conf:
            socat.set_socket_serial(conf["serial_socket"])

        socat.set_workspace(node.workspace.get_workspace())
        socat.init()
        socat.precheck()
        cmd = socat.get_commandline()

        run_command(cmd + " &", True, None, None)
        time.sleep(3)
        logger.info("socat start")
    except CommandRunFailed as e:
        logger.error(e.value)
        raise e
    except InfraSimError as e:
        logger.error(e.value)
        raise e


def stop_socat(conf_file=config.infrasim_default_config):
    socat_stop_cmd = "pkill socat"
    try:
        run_command(socat_stop_cmd, True, None, None)
        logger.info("socat stop")
    except CommandRunFailed:
        logger.error("socat stop failed")
