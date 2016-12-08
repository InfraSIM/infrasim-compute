#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import threading
import re
from . import sshim
from .repl import REPL, register


class iDRACConsole(threading.Thread):
    PROMPT = "/admin1-> "

    def __init__(self, script):
        threading.Thread.__init__(self)
        self.history = []
        self.script = script
        self.response = ''
        self.start()

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

            if groups["cmd"] == "racadm":
                racadm = RacadmConsole()
                racadm.set_input(self.repl_input)
                racadm.set_output(self.repl_output)
                racadm.run()
            elif "exit" in groups["cmd"].lower() or "quit" in groups["cmd"].lower():
                self.script.writeline("Good bye from {}".format(self.__class__.__name__))
                return
            else:
                pass


class RacadmConsole(REPL):

    def __init__(self):
        super(RacadmConsole, self).__init__()
        self.prompt = "racadm>>"

    @register
    def hwinventory(self, ctx, args):
        self.output("hwinventory is not implemented yet")
        return None


if __name__ == "__main__":
    server = sshim.Server(iDRACConsole, port=10022)
    server.run()
