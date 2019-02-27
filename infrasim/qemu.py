'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import time
from infrasim import config
from . import run_command, CommandNotFound, CommandRunFailed, ArgsNotCorrect, InfraSimError
from infrasim.model import CCompute
from infrasim.helper import yaml_load
from .log import infrasim_log, LoggerType

logger_qemu = infrasim_log.get_logger(LoggerType.qemu.value)


def get_qemu():
    try:
        code, qemu_cmd = run_command("which qemu-system-x86_64")
        return qemu_cmd.strip(os.linesep)
    except CommandRunFailed:
        logger_qemu.exception("Cannot find qemu-system-x86_64")
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
        logger_qemu.exception(e.value)
        raise e


def stop_macvtap(eth):
    try:
        run_command("ip link set {} down".format(eth))
        run_command("ip link delete {}".format(eth))
    except CommandRunFailed as e:
        logger_qemu.exception(e.value)
        raise e


def start_qemu(conf_file=config.infrasim_default_config):
    try:
        with open(conf_file, 'r') as f_yml:
            conf = yaml_load(f_yml)
        compute = CCompute(conf["compute"])
        node_name = conf["name"] if "name" in conf else "node-0"

        logger_qemu = infrasim_log.get_logger(
            LoggerType.qemu.value, node_name)

        workspace = os.path.join(config.infrasim_home, node_name)
        if not os.path.isdir(workspace):
            os.mkdir(workspace)
        path_log = os.path.join(config.infrasim_log_dir, node_name)
        compute.logger = infrasim_log.get_logger(LoggerType.model.value, node_name)
        if not os.path.isdir(path_log):
            os.mkdir(path_log)

        sol_enabled = conf["sol_enable"] if "sol_enable" in conf else True

        compute.netns = conf.get("namespace")

        # Set attributes
        compute.enable_sol(sol_enabled)
        compute.set_task_name("{}-node".format(node_name))
        compute.set_log_path(os.path.join(path_log, "qemu.log"))
        compute.set_workspace(workspace)
        compute.set_type(conf["type"])

        # Set interface
        if "type" not in conf:
            raise ArgsNotCorrect("Can't get infrasim type")
        else:
            compute.set_type(conf['type'])

        if "serial_socket" in conf:
            compute.set_socket_serial(conf["serial_socket"])

        if "bmc_connection_port" in conf:
            compute.set_port_qemu_ipmi(conf["bmc_connection_port"])

        if "monitor" not in conf:
            b_enable_monitor = True
        else:
            b_enable_monitor = conf["monitor"].get("enable", True)

        if not isinstance(b_enable_monitor, bool):
            raise ArgsNotCorrect("[Monitor] Invalid setting")
        if b_enable_monitor:
            compute.enable_qemu_monitor()

        compute.init()
        compute.precheck()
        compute.run()

        logger_qemu.info("qemu start")

        return
    except InfraSimError as e:
        logger_qemu.exception(e.value)
        raise e


def stop_qemu(conf_file=config.infrasim_default_config):
    try:
        with open(conf_file, 'r') as f_yml:
            conf = yaml_load(f_yml)
        compute = CCompute(conf["compute"])
        node_name = conf["name"] if "name" in conf else "node-0"

        logger_qemu = infrasim_log.get_logger(LoggerType.qemu.value, node_name)

        # Set attributes
        compute.logger = infrasim_log.get_logger(LoggerType.model.value, node_name)
        compute.set_task_name("{}-node".format(node_name))
        compute.set_log_path(os.path.join(config.infrasim_log_dir, node_name, "qemu.log"))
        compute.set_workspace(os.path.join(config.infrasim_home, node_name))
        compute.set_type(conf["type"])

        # Set interface
        if "type" not in conf:
            raise ArgsNotCorrect("Can't get infrasim type")
        else:
            compute.set_type(conf['type'])

        if "serial_socket" in conf:
            compute.set_socket_serial(conf["serial_socket"])

        if "bmc_connection_port" in conf:
            compute.set_port_qemu_ipmi(conf["bmc_connection_port"])

        compute.init()
        compute.terminate()

        logger_qemu.info("qemu stopped")
    except InfraSimError as e:
        logger_qemu.exception(e.value)
        raise e
