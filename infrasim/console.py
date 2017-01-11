'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import threading
import os
import sys
from . import sshim
from . import logger
from .ipmicons.command import Command_Handler
from .ipmicons.common import msg_queue
from .ipmicons import env

import re

from ipmicons import sdr, common
import daemon
from infrasim import config
import signal
from .ipmicons.common import IpmiError

server = None


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


def _start_console(instance="default"):
    global server
    server = sshim.Server(IPMI_CONSOLE, port=env.PORT_SSH_FOR_CLIENT)
    try:
        logger.info("ipmi-console start {}".format(instance))
        server.run()

    except KeyboardInterrupt:
        server.stop()


def _stop_console():
    if server:
        server.stop()

sensor_thread_list = []


def _spawn_sensor_thread():
    for sensor_obj in sdr.sensor_list:
        if sensor_obj.get_event_type() == "threshold":
            t = threading.Thread(target=sensor_obj.execute)
            t.setDaemon(True)
            sensor_thread_list.append(t)
            common.logger.info('spawn a thread for sensor ' +
                               sensor_obj.get_name())
            t.start()


def _free_resource():
    # close telnet session
    # common.close_telnet_session()

    # join the sensor thread
    for sensor_obj in sdr.sensor_list:
        sensor_obj.set_mode("user")
        # set quit flag
        sensor_obj.set_quit(True)
        # acquire the lock that before notify
        sensor_obj.condition.acquire()
        sensor_obj.condition.notify()
        sensor_obj.condition.release()

    for thread in sensor_thread_list:
        thread.join()


def start(instance="default"):
    """
    Attach ipmi-console to target instance specified by
    its name
    :param instance: infrasim instance name
    """
    # initialize logging
    common.init_logger(instance)
    # initialize environment
    try:
        common.init_env(instance)
    except IpmiError, e:
        print e.value
        return
    daemon.daemonize("{}/{}/.ipmi_console.pid".format(config.infrasim_home, instance))
    # parse the sdrs and build all sensors
    sdr.parse_sdrs()
    # running thread for each threshold based sensor
    _spawn_sensor_thread()
    _start_console(instance)


def stop(instance="default"):
    """
    Stop ipmi-console of target instance specified by
    its name
    :param instance: infrasim instance name
    """
    try:
        file_ipmi_console_pid = "{}/{}/.ipmi_console.pid".\
            format(config.infrasim_home, instance)
        with open(file_ipmi_console_pid, "r") as f:
            pid = f.readline().strip()

        os.kill(int(pid), signal.SIGTERM)
        os.remove(file_ipmi_console_pid)
    except:
        pass


def console_main(instance="default"):
    if len(sys.argv) < 2:
        print "ipmi-console [ start | stop ]"
        sys.exit(1)
    if len(sys.argv) >= 3:
        if sys.argv[2] == "-h":
            print "ipmi-console [ start | stop ] [ node_name ]"
            sys.exit(1)
        else:
            instance = sys.argv[2]
    if sys.argv[1] == "start":
        start(instance)
    elif sys.argv[1] == "stop":
        stop(instance)
    else:
        pass
