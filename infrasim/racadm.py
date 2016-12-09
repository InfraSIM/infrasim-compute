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


class iDRACConsole(threading.Thread):
    PROMPT = "/admin1-> "

    def __init__(self, script):
        threading.Thread.__init__(self)
        self.history = []
        self.script = script
        self.response = ''
        self.start()
        self.server = None

    def welcome(self):
        self.script.writeline("Connecting to {ip}:{port}...")
        self.script.writeline("Connection established.")
        self.script.writeline("To escape to local shell, press \'Ctrl+Alt+]\'.")
        self.script.writeline("")

    def repl_input(self, msg):
        self.script.write(msg)
        groups = self.script.expect(re.compile('(?P<cmd>.*)')).groupdict()
        return groups["cmd"]

    def repl_output(self, msg):
        for line in msg.splitlines():
            self.script.writeline(line)

    def run(self):
        self.welcome()
        while True:
            self.script.write(self.PROMPT)
            groups = self.script.expect(re.compile('(?P<cmd>.*)')).groupdict()
            cmds = groups["cmd"].split()

            if len(cmds) == 0:
                pass
            elif cmds[0] == "racadm" and len(cmds) == 1:
                racadm = RacadmConsole()
                racadm.set_input(self.repl_input)
                racadm.set_output(self.repl_output)
                racadm.run()
            elif cmds[0] == "racadm":
                racadm = RacadmConsole()
                racadm.set_output(self.repl_output)
                racadm_cmd = parse(" ".join(cmds[1:]))
                racadm.output(racadm.do(racadm_cmd))
            elif cmds[0].lower() in ["exit", "quit"]:
                self.script.writeline("Good bye from {}".format(self.__class__.__name__))
                return
            else:
                self.script.writeline("Support commands:")
                self.script.writeline("\thelp")
                self.script.writeline("\tracadm")
                self.script.writeline("\texit")
                self.script.writeline("\tquit")


class RacadmConsole(REPL):

    def __init__(self):
        super(RacadmConsole, self).__init__()
        self.prompt = "racadm>>"

    @register
    def hwinventory(self, ctx, args):
        return "hwinventory is not implemented yet"


class iDRACHandler(sshim.Handler):

    def check_auth_none(self, username):
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        return auth(username, password)


if __name__ == "__main__":
    server = sshim.Server(iDRACConsole, port=10022, handler=iDRACHandler)
    server.run()
