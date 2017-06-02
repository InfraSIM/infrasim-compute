#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import threading
import re
import paramiko
import os
import logging
from os import linesep
from infrasim import sshim, logger, config
from . import env
from .api import iDRACConsole


def auth(username, password):
    if username in env.auth_map and env.auth_map[username] == password:
        return paramiko.AUTH_SUCCESSFUL
    else:
        return paramiko.AUTH_FAILED


def init_log():
    """
    Create log folder, prepare handler and recording level
    """
    env.r_log = logging.getLogger(__name__)

    log_folder = os.path.join(config.infrasim_logdir, env.node_name)
    if not os.path.exists(log_folder):
        os.mkdir(log_folder)
    log_path = os.path.join(log_folder, "racadmsim.log")

    r_hdl = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    r_hdl.setFormatter(formatter)
    env.r_log.addHandler(r_hdl)
    env.r_log.setLevel(logging.NOTSET)


class iDRACHandler(sshim.Handler):
    def __init__(self, server, connection):
        # paramiko.ServerInterface.start_server() raise exception
        # and make server instance quite.
        # Here the exception is captured in case of a service stop
        try:
            super(iDRACHandler, self).__init__(server, connection)
        except Exception:
            pass

    def check_auth_none(self, username):
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        return auth(username, password)

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED

    def check_channel_exec_request(self, channel, command):
        cmds = command.split()
        with channel:
            # If commands is racadmsim, go to racadmsim console
            if cmds == ["racadm"]:
                channel.send("SSH to iDRAC {}:{} then go to racadmsim console.{}".
                             format(self.address, self.server.port, linesep))
            # else, execute command and response
            else:
                idrac = iDRACConsole()
                idrac.set_output(channel.sendall)
                rsp = idrac.do(cmds)
                idrac.output(rsp)

        return True


class iDRACServer(threading.Thread):
    PROMPT = "/admin1-> "

    def __init__(self, script):
        threading.Thread.__init__(self)
        self.history = []
        self.script = script
        self.response = ''
        self.start()
        self.server = None

    def repl_input(self, msg):
        self.script.write(msg)
        groups = self.script.expect(re.compile('(?P<cmd>.*)')).groupdict()
        logger_r.info("command rev: {}".format(groups['cmd']))
        return groups["cmd"]

    def repl_output(self, msg):
        for line in msg.splitlines():
            self.script.writeline(line)

    def run(self):
        idrac = iDRACConsole()
        idrac.set_input(self.repl_input)
        idrac.set_output(self.repl_output)
        idrac.run()


def start(instance="default",
          ipaddr="",
          port=10022,
          username="admin",
          password="admin",
          data_src="auto"):
    # Init environment
    env.auth_map[username] = password
    env.node_name = instance
    if os.path.exists(data_src):
        env.racadm_data = data_src
    init_log()
    print env.r_log
    server = sshim.Server(iDRACServer,
                          logger=logger_r,
                          address=ipaddr,
                          port=int(port),
                          handler=iDRACHandler)
    logger.info("{}-racadm start on ip: {}, port: {}".
                format(env.node_name, ipaddr, port))
    server.run()

if __name__ == "__main__":
    # Try to run this from code root directory, with command:
    #     python -m infrasim.racadmsim
    env.auth_map["admin"] = "admin"
    env.node_name = "default"
    init_log()

    auth_map["admin"] = "admin"
    server = sshim.Server(iDRACServer, logger=logger_r, port=10022, handler=iDRACHandler)
    server.run()
