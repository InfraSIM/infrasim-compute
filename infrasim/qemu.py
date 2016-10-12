#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import yaml
import time
import config
from . import run_command, logger, CommandNotFound, CommandRunFailed, ArgsNotCorrect
from model import CCompute


def get_qemu():
    try:
        code, qemu_cmd = run_command("which qemu-system-x86_64")
        return qemu_cmd.strip(os.linesep)
    except CommandRunFailed:
        raise CommandNotFound("qemu-system-x86_64")


def status_qemu():
    try:
        run_command("pidof qemu-system-x86_64")
        print "Infrasim Qemu service is running"
    except CommandRunFailed:
        print "Inrasim Qemu service is stopped"


def create_macvtap(idx, nic, mac):
    try:
        run_command("ip link add link {} name macvtap{} type macvtap mode bridge".format(nic, idx))
        run_command("ip link set macvtap{} address {} up".format(idx, mac))
        run_command("ifconfig macvtap{} promisc".format(idx))
        time.sleep(1)
    except CommandRunFailed as e:
        raise e


def stop_macvtap(eth):
    try:
        run_command("ip link set {} down".format(eth))
        run_command("ip link delete {}".format(eth))
    except CommandRunFailed as e:
        raise e


def start_qemu(conf_file=config.infrasim_initial_config):
    try:
        with open(conf_file, 'r') as f_yml:
            conf = yaml.load(f_yml)
        compute = CCompute(conf["compute"])
        node_name = conf["name"] if "name" in conf else "node-0"
        workspace = "{}/.infrasim/{}".format(os.environ["HOME"], node_name)
        if not os.path.isdir(workspace):
            os.mkdir(workspace)
        path_log = "/var/log/infrasim/{}".format(node_name)
        if not os.path.isdir(path_log):
            os.mkdir(path_log)

        # Set attributes
        compute.set_task_name("{}-node".format(node_name))
        compute.set_log_path("/var/log/infrasim/{}/qemu.log".
                             format(node_name))
        compute.set_workspace("{}/.infrasim/{}".
                              format(os.environ["HOME"], node_name))
        compute.set_type(conf["type"])

        # Set interface
        if "type" not in conf:
            raise ArgsNotCorrect("Can't get infrasim type")
        else:
            compute.set_type(conf['type'])

        if "serial_port" in conf:
            compute.set_port_serial(conf["serial_port"])

        if "bmc_connection_port" in conf:
            compute.set_port_qemu_ipmi(conf["bmc_connection_port"])

        compute.init()
        compute.precheck()
        compute.run()

        logger.info("qemu start")

        return
    except CommandRunFailed as e:
        logger.error(e.value)
        raise e
    except ArgsNotCorrect as e:
        logger.error(e.value)
        raise e


def stop_qemu(conf_file=config.infrasim_initial_config):
    try:
        with open(conf_file, 'r') as f_yml:
            conf = yaml.load(f_yml)
        compute = CCompute(conf["compute"])
        node_name = conf["name"] if "name" in conf else "node-0"

        # Set attributes
        compute.set_task_name("{}-node".format(node_name))
        compute.set_log_path("/var/log/infrasim/{}/qemu.log".
                             format(node_name))
        compute.set_workspace("{}/.infrasim/{}".
                              format(os.environ["HOME"], node_name))
        compute.set_type(conf["type"])

        # Set interface
        if "type" not in conf:
            raise ArgsNotCorrect("Can't get infrasim type")
        else:
            compute.set_type(conf['type'])

        if "serial_port" in conf:
            compute.set_port_serial(conf["serial_port"])

        if "bmc_connection_port" in conf:
            compute.set_port_qemu_ipmi(conf["bmc_connection_port"])

        compute.init()
        compute.terminate()

        logger.info("qemu stopped")
    except Exception, e:
        logger.error(e.value)
        raise e
