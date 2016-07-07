#!/usr/bin/env python
# -*- coding: utf-8 -*-


from . import sshim
from . import run_command, logger
from .ipmicons.command import Command_Handler
from .ipmicons.common import msg_queue

import re, shlex, threading
from datetime import datetime

class IPMI_CONSOLE(threading.Thread):
    WELCOME = 'You have connected to the test server.'
    PROMPT = "IPMI_SIM> "
    def __init__(self, script):
        threading.Thread.__init__(self)
        self.history = []
        self.script = script
        self.command_handler = Command_Handler()
        self.response = ''
        self.start()

    def welcome(self):
        self.script.writeline(self.WELCOME)

    def prompt(self):
        self.script.write(self.PROMPT)

    def writeresponse(self, rspstr):
        """ Save the response string."""
        self.response += rspstr

    def usingHandler(self, cmd):
        """ Using the Command_Handler from command module to handle command."""
        self.command_handler.handle_command(cmd)
        while msg_queue.empty() is False:
            self.writeresponse(msg_queue.get())

    def run(self):
        self.welcome()
        while True:
            self.response = ""
            self.prompt()
            groups = self.script.expect(re.compile('(?P<input>.*)')).groupdict()
            try:
                cmdline = groups['input'].encode('ascii', 'ignore')
            except:
                continue

            if not cmdline or len(cmdline) == 0:
                continue

            try:
                cmd = cmdline.split()[0]

                if cmd.upper() == 'EXIT' \
                        or cmd.upper() == 'QUIT':
                    self.script.writeline("Quit!")
                    break

                self.command_handler.handle_command(cmdline)
                while msg_queue.empty() is False:
                    self.writeresponse(msg_queue.get())

                if len(self.response):
                    lines = self.response.split('\n')
                    for line in lines:
                        self.script.writeline(line)
            except:
                continue


def start_console():
    server = sshim.Server(IPMI_CONSOLE, port=9300)
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop()

    logger.info("ipmi_console start")

def stop_console():
    console_stop_cmd = "pkill ipmi_console"
    run_command(console_stop_cmd, True, None, None)
    logger.info("ipmi_console stop")


