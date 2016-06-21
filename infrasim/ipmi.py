#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, subprocess, sys, signal
import infrasim

def ipmi_check_pid():
    cmd  = "ps ax | grep ipmi_sim"
    pipe_list = subprocess.check_output(cmd, shell=True).split("\n")
    for pipe in pipe_list:
        if len(pipe) > 100:
            return pipe
    return None

def ipmi_start(node="quanta_d51"):
    if ipmi_check_pid() is not None:
        print "inframsim_ipmi service is already running"
        return 0

    cmd = "ipmi_sim -c /etc/infrasim/vbmc.conf -f /usr/local/etc/infrasim/{0}/{0}.emu -n &"
    cmd = cmd.format(node)
    cmd_list = cmd.split(' ')
    os.system(cmd)

    #os.system("gunicorn -w 4 infrasim:app -b :80 -D")

def ipmi_stop():
    status = ipmi_check_pid()
    if status is None:
        print "infrasim-ipmi service is OFF"
    else:
        os.system("pkill ipmi_sim")
    os.system("pkill gunicorn")
    os.system("infrasim-vm stop")
    print "infrasim-ipmi service stopped!"

def ipmi_status():
    status = ipmi_check_pid()
    if status is None:
        print "infrasim-ipmi service is OFF"
        return 0

    print "infrasim-ipmi service is ON"
    return 1


def ipmi_help():
    print "inframsim_ipmi start|stop|status"

