#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import os


def run_command(cmd="", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    :param cmd: the command should run
    :param shell: if the type of cmd is string, shell should be set as True, otherwise, False
    :param stdout: reference subprocess module
    :param stderr: reference subprocess module
    :return: tuple (return code, output)
    """
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


def get_socat():
    socat_cmd_returncode, socat_cmd = run_command("which socat")
    if socat_cmd_returncode:
        install_returncode, install_output = run_command("apt-get install socat")
        if not install_returncode:
            socat_cmd_returncode, socat_cmd = run_command("which socat")
        else:
            print "install error"
            raise Exception("socat install Error")
    return socat_cmd.strip(os.linesep)


def start_socat():
    socat_cmd = get_socat()
    socat_start_cmd = "{} pty,link=/etc/infrasim/pty0,waitslave tcp-listen:9003," \
                      "forever,reuseaddr,fork &".format(socat_cmd)
    run_command(socat_start_cmd, True, None, None)


def stop_socat():
    socat_stop_cmd = "pkill socat"
    run_command(socat_stop_cmd, True, None, None)
