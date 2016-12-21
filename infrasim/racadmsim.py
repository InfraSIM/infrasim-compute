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
from os import linesep
from . import sshim, logger
from .repl import REPL, register, parse, QuitREPL

auth_map = {}


def auth(username, password):
    global auth_map
    if username in auth_map and auth_map[username] == password:
        return paramiko.AUTH_SUCCESSFUL
    else:
        return paramiko.AUTH_FAILED


class RacadmConsole(REPL):

    def __init__(self):
        super(RacadmConsole, self).__init__()
        self.prompt = "racadmsim>>"

    def refine_cmd(self, cmd):
        """
        For racadm console, it allows write racadm as prefix.
        So when you enter `racadm getled`, you actually run
        `getled`, the cmd need to be revised.
        """
        while True:
            if cmd and cmd[0] == "racadm":
                del cmd[0]
            else:
                return cmd

    @register
    def hwinventory(self, ctx, args):
        return "hwinventory is not implemented yet"

    def run(self):
        self.welcome()
        while True:
            # READ
            inp = self.input(self.prompt)

            # EVAL
            cmd = self.refine_cmd(parse(inp))

            try:
                out = self.do(cmd)
            except EOFError:
                return
            except QuitREPL:
                return

            # PRINT
            self.output(linesep)
            self.output(" ".join(["racadm"]+cmd))
            if out is not None:
                self.output(out)
                self.output(linesep)


class iDRACConsole(REPL):

    def __init__(self):
        super(iDRACConsole, self).__init__()
        self.prompt = "/admin1-> "

    def welcome(self):
        lines = ["Connecting to {ip}:{port}...",
                 "Connection established.",
                 "To escape to local shell, press \'Ctrl+Alt+]\'.",
                 "", ""]
        self.output(linesep.join(lines))

    @register
    def racadm(self, ctx, args):
        """
        Enter racadmsim console or call sub commands
        """
        if len(args) == 1:
            racadm = RacadmConsole()
            racadm.set_input(self.input)
            racadm.set_output(self.output)
            racadm.run()
        else:
            racadm = RacadmConsole()
            racadm.set_output(self.output)
            racadm_cmd = parse(" ".join(args[1:]))
            racadm.output(racadm.do(racadm_cmd).strip(linesep))


class iDRACHandler(sshim.Handler):

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
            if cmds == ["racadmsim"]:
                channel.send("SSH to iDRAC {}:{} then go to racadmsim console.{}".
                             format(self.address, self.server.port, linesep))
            # else, execute command and response
            else:
                idrac = iDRACConsole()
                idrac.set_output(channel.send)
                idrac.output(idrac.do(cmds))

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
          password="admin"):
    # Init environment
    global auth_map
    auth_map[username] = password

    server = sshim.Server(iDRACServer,
                          address=ipaddr,
                          port=int(port),
                          handler=iDRACHandler)
    logger.info("{}-racadm start".format(instance))
    server.run()

if __name__ == "__main__":
    server = sshim.Server(iDRACServer, port=10022, handler=iDRACHandler)
    server.run()
