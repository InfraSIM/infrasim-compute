#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import subprocess

VM_DEFAULT_CONFIG = "/etc/infrasim/infrasim.yml"

logger = logging.getLogger()
hdlr = logging.FileHandler('/var/log/inframsim.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.NOTSET)


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
        result = ""
        if cmd_result[1] is not None:
            result = cmd + ":" + cmd_result[1]
        else:
            result = cmd
        logger.error(result)
        raise CommandRunFailed(result)
    return 0, cmd_result[0]


def has_option(config, *args):
    """
    Check if config has these option chains
    :param config: a python dict
    :param args: a list of option chains, e.g.
    if config is:
    {
        "a": {"b": 1}
    }
    has_option(config, "a", "b") returns True
    has_option(config, "b") returns False
    has_option(config, "a", "c") returns False
    """
    if len(args) == 0:
        raise Exception(has_option.__doc__)
    section = config
    for option in args:
        try:
            iter(section)
        except TypeError:
            return False
        if option in section:
            section = section[option]
        else:
            return False
    return True


class InfraSimError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class CommandNotFound(InfraSimError):
    pass


class PackageNotFound(InfraSimError):
    pass


class CommandRunFailed(InfraSimError):
    pass


class ArgsNotCorrect(InfraSimError):
    pass
