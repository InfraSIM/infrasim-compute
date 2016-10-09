#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import yaml
import config
from . import run_command, logger, ArgsNotCorrect, CommandNotFound, CommandRunFailed
from model import CBMC, CNode


def get_ipmi():
    try:
        code, ipmi_cmd = run_command("which ipmi_sim")
        return ipmi_cmd.strip(os.linesep)
    except CommandRunFailed:
        raise CommandNotFound("ipmi_sim")


def status_ipmi():
    try:
        run_command("pidof ipmi_sim")
        print "InfraSim IPMI service is running"
    except CommandRunFailed:
        print "Infrasim IPMI service is stopped"


def start_ipmi(conf_file=config.infrasim_initial_config):
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


def stop_ipmi(conf_file=config.infrasim_initial_config):
    ipmi_stop_cmd = "pkill ipmi_sim"
    try:
        run_command(ipmi_stop_cmd, True, None, None)
        logger.info("ipmi stopped")
    except CommandRunFailed:
        logger.error("ipmi stop failed")
