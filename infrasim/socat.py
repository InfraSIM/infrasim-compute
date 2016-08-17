#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, time
from . import run_command, logger, CommandNotFound, CommandRunFailed

def get_socat():
    try:
        code, socat_cmd = run_command("which socat")
        return socat_cmd.strip(os.linesep)
    except CommandRunFailed as e:
        raise CommandNotFound("/usr/bin/socat")

def status_socat():
    try:
        run_command("pidof socat")
        print "Infrasim Socat service is running"
    except CommandRunFailed as e:
        print "Inrasim Socat service is stopped"

def start_socat():
    socat_cmd = get_socat()
    socat_start_cmd = "{} pty,link=/etc/infrasim/pty0,waitslave udp-listen:9003," \
                      "reuseaddr,fork &".format(socat_cmd)
    try:
        run_command(socat_start_cmd, True, None, None)
        time.sleep(3)
        logger.info("socat start")
    except CommandRunFailed as e:
        raise e

def stop_socat():
    socat_stop_cmd = "pkill socat"
    try:
        run_command(socat_stop_cmd, True, None, None)
        logger.info("socat stop")
    except CommandRunFailed as e:
        logger.error("socat stop failed")
