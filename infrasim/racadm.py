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
from . import sshim
from .repl import REPL, register, parse


def auth(username, password):
    CREDENTIAL = {"ru": "rp"}
    if username in CREDENTIAL and CREDENTIAL[username] == password:
        return paramiko.AUTH_SUCCESSFUL
    elif username in CREDENTIAL:
        return paramiko.AUTH_PARTIALLY_SUCCESSFUL
    else:
        return paramiko.AUTH_FAILED


class RacadmConsole(REPL):

    def __init__(self):
        super(RacadmConsole, self).__init__()
        self.prompt = "racadm>>"

    @register
    def hwinventory(self, ctx, args):
        return "hwinventory is not implemented yet"


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
        Enter racadm console or call racadm sub command
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

    def check_channel_exec_request(self, channel, command):
        cmds = command.split()

        with channel:
            # If commands is racadm, go to racadm console
            if cmds == ["racadm"]:
                channel.send("SSH to iDRAC {}:{} then go to racadm console.{}".
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
        self.script.write("Exception here")
        raise Exception("Here")
        idrac = iDRACConsole()
        idrac.set_input(self.repl_input)
        idrac.set_output(self.repl_output)
        idrac.run()


if __name__ == "__main__":
    server = sshim.Server(iDRACServer, port=10022, handler=iDRACHandler)
    server.run()
