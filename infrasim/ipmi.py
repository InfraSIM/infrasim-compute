#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from . import run_command, logger

def get_ipmi():
    code, ipmi_cmd = run_command("which /usr/local/bin/ipmi_sim")
    if code == -1:
        raise Exception("ipmi_sim install Error")
    return ipmi_cmd.strip(os.linesep)

def start_ipmi(node):
    ipmi_cmd = get_ipmi()
    ipmi_start_cmd = "{0} -c /etc/infrasim/vbmc.conf" \
                    " -f /usr/local/etc/infrasim/{1}/{1}.emu -n -s /var/tmp &".format(ipmi_cmd, node)
    code, reason =  run_command(ipmi_start_cmd, True, None, None)
    if code == 0:
        logger.info("ipmi start")
        logger.info(reason)
    else:
        logger.error(reason)

def stop_ipmi():
    ipmi_stop_cmd = "pkill ipmi_sim"
    code, reason = run_command(ipmi_stop_cmd, True, None, None)
    if code == 0:
        logger.info("ipmi stopped")
    else:
        logger.error(reason)
