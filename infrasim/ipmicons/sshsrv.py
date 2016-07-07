'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import re
import sshim
import threading

import command
import common


class SSHHandler(object):
    """ SSH handlelr based on SSHIIM."""
    WELCOME = ''
    PROMPT = ''

    def __init__(self, handler=None, prompt='CMD> ', port=20022):

        self.port = port
        if self.PROMPT:
            self.prompt = self.PROMPT
        else:
            self.prompt = prompt
        self.server = sshim.Server(self.handle_command, port=int(self.port))
        self.response = ''

        if handler is None:
            handler = self

        self.command_handler = command.Command_Handler()
        self.thread_stop = threading.Event()

    def stop(self):
        """ Stop the thread."""
        self.thread_stop.set()
        self.server.stop()

    def writeresponse(self, rspstr):
        """ Save the response string."""
        self.response += rspstr

    def usingHandler(self, cmd):
        """ Using the Command_Handler from command module to handle command."""
        self.command_handler.handle_command(cmd)
        while common.msg_queue.empty() is False:
            self.writeresponse(common.msg_queue.get())

    def handle_command(self, script):
        """ Handle the command receive from user."""

        if self.WELCOME:
            script.writeline(self.WELCOME)
        while not self.thread_stop.is_set():
            self.response = ''
            script.write(self.prompt)
            groups = script.expect(re.compile('(?P<input>.*)')).groupdict()
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
                    script.writeline("Quit!")
                    break

                self.usingHandler(cmdline)

                if len(self.response):
                    lines = self.response.split('\n')
                    for line in lines:
                        script.writeline(line)
            except:
                continue

    def serve_forever(self):
        """ Run the SSH server."""
        try:
            self.server.run()
        except KeyboardInterrupt:
            self.stop()
