#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import yaml
from . import run_command, logger, ArgsNotCorrect, CommandNotFound, CommandRunFailed, VM_DEFAULT_CONFIG
from model import CBMC, CNode


def get_ipmi():
    try:
        code, ipmi_cmd = run_command("which /usr/local/bin/ipmi_sim")
        return ipmi_cmd.strip(os.linesep)
    except CommandRunFailed as e:
        raise CommandNotFound("/usr/local/bin/ipmi_sim")


def status_ipmi():
    try:
        run_command("pidof ipmi_sim")
        print "InfraSim IPMI service is running"
    except CommandRunFailed as e:
        print "Infrasim IPMI service is stopped"


def start_ipmi(conf_file=VM_DEFAULT_CONFIG):
    try:
        with open(conf_file, 'r') as f_yml:
            conf = yaml.load(f_yml)

        node = CNode(conf)
        if "name" in conf:
            node.set_node_name(conf["name"])
        node.init_workspace()

        bmc = CBMC(conf.get('bmc', {}))
        node_name = conf["name"] if "name" in conf else "node-0"
        bmc.set_task_name("{}-bmc".format(node_name))
        bmc.set_log_path("/var/log/infrasim/{}/openipmi.log".
                         format(node_name))
        bmc.set_type(conf["type"])
        bmc.set_workspace(node.workspace)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()
        cmd = bmc.get_commandline()
        logger.debug(cmd)
        run_command(cmd+" &", True, None, None)

        logger.info("bmc start")
    except CommandRunFailed as e:
        logger.error(e.value)
        raise e
    except ArgsNotCorrect as e:
        logger.error(e.value)
        raise e


def stop_ipmi(conf_file=VM_DEFAULT_CONFIG):
    ipmi_stop_cmd = "pkill ipmi_sim"
    try:
        run_command(ipmi_stop_cmd, True, None, None)
        logger.info("ipmi stopped")
    except CommandRunFailed as e:
        logger.error("ipmi stop failed")
