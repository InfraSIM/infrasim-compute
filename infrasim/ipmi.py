#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from . import run_command, logger, CommandNotFound, CommandRunFailed

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
 
def start_ipmi(node):
    ipmi_cmd = get_ipmi()
    ipmi_start_cmd = "{0} -c /etc/infrasim/vbmc.conf" \
                    " -f /usr/local/etc/infrasim/{1}/{1}.emu -n -s /var/tmp > /var/tmp/openipmi.log &".format(ipmi_cmd, node)
    try:
        run_command(ipmi_start_cmd, True, None, None)
        logger.info("ipmi start")
    except CommandRunFailed as e:
        raise e

def stop_ipmi():
    ipmi_stop_cmd = "pkill ipmi_sim"
    try:
        run_command(ipmi_stop_cmd, True, None, None)
        logger.info("ipmi stopped")
    except CommandRunFailed as e:
        logger.warning("ipmi stop failed")
