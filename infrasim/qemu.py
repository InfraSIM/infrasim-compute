#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import socket
import time
import netifaces
from . import run_command, logger, CommandNotFound, CommandRunFailed, ArgsNotCorrect, has_option
from model import CCompute

VM_DEFAULT_CONFIG = "/etc/infrasim/infrasim.yml"


def get_qemu():
    try:
        code, qemu_cmd = run_command("which /usr/local/bin/qemu-system-x86_64")
        return qemu_cmd.strip(os.linesep)
    except CommandRunFailed as e:
        raise CommandNotFound("/usr/local/bin/qemu-system-x86_64")


def status_qemu():
    try:
        run_command("pidof qemu-system-x86_64")
        print "Infrasim Qemu service is running"
    except CommandRunFailed as e:
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


def start_qemu(conf=VM_DEFAULT_CONFIG):
    try:
        with open(conf, 'r') as f_yml:
            conf = yaml.load(f_yml)
        compute = CCompute(conf["compute"])
        compute.init()
        compute.precheck()
        cmd = "{} 2>/var/tmp/qemu.log &".format(compute.get_commandline())
        logger.debug(cmd)
        run_command(cmd, True, None, None)

        logger.info("qemu start")
    except CommandRunFailed as e:
        logger.error(e.value)
        raise e
    except ArgsNotCorrect as e:
        logger.error(e.value)
        raise e


def stop_qemu():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1",  2345))
        sock.send("quit\n")
        sock.close()
    except Exception, e:
        pass
    logger.info("qemu stopped")
