#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, time
from . import run_command

def get_socat():
    code, socat_cmd = run_command("which socat")
    if code:
        code, install_cmd = run_command("apt-get install socat")
        if not code:
            code, socat_cmd = run_command("which socat")
        else:
            raise Exception("socat install Error")
    return socat_cmd.strip(os.linesep)


def start_socat():
    socat_cmd = get_socat()
    socat_start_cmd = "{} pty,link=/etc/infrasim/pty0,waitslave tcp-listen:9003," \
                      "forever,reuseaddr,fork &".format(socat_cmd)
    run_command(socat_start_cmd, True, None, None)
    time.sleep(5)

def stop_socat():
    socat_stop_cmd = "pkill socat"
    run_command(socat_stop_cmd, True, None, None)
