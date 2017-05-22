'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import threading
import os
import sys
import re
import signal
import time

from infrasim import daemon
from infrasim import sshim
from infrasim import config
from .command import Command_Handler
from .common import msg_queue
from .common import IpmiError
import env, sdr, common
from infrasim.log import infrasim_log, LoggerType

server = None
logger_ic = infrasim_log.get_logger(LoggerType.ipmi_console.value)


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
                logger_ic.info("command rev: {}".format(cmdline))
                if cmd.upper() == 'EXIT' \
                        or cmd.upper() == 'QUIT':
                    self.script.writeline("Quit!")
                    logger_ic.info("command res: quit is finished")
                    break

                self.command_handler.handle_command(cmdline)
                while msg_queue.empty() is False:
                    self.writeresponse(msg_queue.get())

                if len(self.response):
                    lines = self.response.split('\n')
                    for line in lines:
                        self.script.writeline(line)
                        logger_ic.info(line)
                logger_ic.info("command res: "
                               "command response is finished.")
            except:
                continue


def _start_console(instance="default"):
    global logger_ic
    logger_ic = infrasim_log.get_logger(LoggerType.ipmi_console.value, instance)
    global server
    server = sshim.Server(IPMI_CONSOLE, logger_ic, port=env.PORT_SSH_FOR_CLIENT)
    try:
        logger_ic.info("command res: ipmi-console start {} "
                       "is finished".format(instance))
        server.run()

    except KeyboardInterrupt as e:
        logger_ic.error("{} \nstart to stop ipmi-console".format(str(e)))
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
    global logger_ic
    logger_ic = infrasim_log.get_logger(LoggerType.ipmi_console.value, instance)
    common.init_logger(instance)
    # initialize environment
    common.init_env(instance)

    daemon.daemonize("{}/{}/.ipmi_console.pid".format(config.infrasim_home, instance))
    # parse the sdrs and build all sensors
    sdr.parse_sdrs()
    # running thread for each threshold based sensor
    _spawn_sensor_thread()
    _start_monitor(instance)
    _start_console(instance)


def monitor(instance="default"):
    """
    Target method used by monitor thread, which polls vbmc status every 3s.
    If vbmc stops, ipmi-console will stop.
    :param instance: infrasim node name
    """
    while True:
        try:
            with open("{}/{}/.{}-bmc.pid".format(
                    config.infrasim_home, instance, instance), "r") as f:
                pid = f.readline().strip()
                if not os.path.exists("/proc/{}".format(pid)):
                    break
            time.sleep(3)
        except IOError:
            break
    stop(instance)


def _start_monitor(instance="default"):
    """
    Create a monitor thread to watch vbmc status.
    :param instance: infrasim node name
    """
    global logger_ic
    logger_ic = infrasim_log.get_logger(LoggerType.ipmi_console.value, instance)
    logger_ic.info("ipmi-console monitor thread starts to run.")
    monitor_thread = threading.Thread(target=monitor, args=(instance,))
    monitor_thread.setDaemon(True)
    monitor_thread.start()


def stop(instance="default"):
    """
    Stop ipmi-console of target instance specified by
    its name
    :param instance: infrasim instance name
    """
    global logger_ic
    logger_ic = infrasim_log.get_logger(LoggerType.ipmi_console.value, instance)

    try:
        file_ipmi_console_pid = "{}/{}/.ipmi_console.pid".\
            format(config.infrasim_home, instance)
        with open(file_ipmi_console_pid, "r") as f:
            pid = f.readline().strip()

        os.remove(file_ipmi_console_pid)

        os.kill(int(pid), signal.SIGTERM)
    except:
        pass


def console_main(instance="default"):
    """
        Usage: ipmi-console [start | stop ] [ node_name ]
        node_name is optional.
    """
    global logger_ic
    cmdline = 'ipmi-console '
    for word in sys.argv[1:]:
        cmdline += word+" "
    try:
        arg_num = len(sys.argv)
        if arg_num < 2 or arg_num > 3:
            logger_ic.info('command rev: {}'.format(cmdline))
            logger_ic.error(console_main.__doc__)
            raise IpmiError("{}".format(console_main.__doc__))
        if arg_num == 3:
            if sys.argv[2] == "-h":
                logger_ic.info('command rev: {}'.format(cmdline))
                print console_main.__doc__
                logger_ic.info('command res: have shown the help')
                sys.exit()
            instance = sys.argv[2]
        logger_ic = infrasim_log.get_logger(
            LoggerType.ipmi_console.value, instance)
        logger_ic.info('command res: {}'.format(cmdline))
        if sys.argv[1] == "start":
            start(instance)
        elif sys.argv[1] == "stop":
            stop(instance)
            logger_ic.info("command res: stop ipmi-console is finished.")
        else:
            logger_ic.error(console_main.__doc__)
            raise IpmiError("{}".format(console_main.__doc__))

    except Exception as e:
        sys.exit(e)

