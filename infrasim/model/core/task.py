'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
import time
import signal
import shlex
import subprocess
import fcntl
from infrasim import CommandRunFailed
from infrasim.log import infrasim_log, LoggerType
from infrasim.helper import run_in_namespace, double_fork


class Task(object):
    def __init__(self):
        # priroty should be range from 0 to 5
        # +-----+-----+-----+----+-----+
        # |  0  |  1  |  2  |  3 |  4  |
        # +-----+-----+-----+----+-----+
        # |High |                | Low |
        # +-----+-----+-----+----+-----+
        self.__task_priority = None
        self.__workspace = None
        self.__task_name = None
        self.__log_path = ""
        self.__logger = infrasim_log.get_logger(LoggerType.model.value)

        # If any task set the __asyncronous to True,
        # this task shall only be maintained with information
        # no actual run shall be taken
        self.__asyncronous = False
        self.__netns = None

    @property
    def netns(self):
        return self.__netns

    @netns.setter
    def netns(self, ns):
        self.__netns = ns

    def set_priority(self, priority):
        self.__task_priority = priority

    def get_priority(self):
        return self.__task_priority

    def set_task_name(self, name):
        self.__task_name = name

    def get_task_name(self):
        return self.__task_name

    def get_commandline(self):
        self.__logger.exception("get_commandline not implemented")
        raise NotImplementedError("get_commandline not implemented")

    def set_workspace(self, directory):
        self.__workspace = directory

    def get_workspace(self):
        return self.__workspace

    def set_log_path(self, log_path):
        self.__log_path = log_path

    @property
    def logger(self):
        return self.__logger

    @logger.setter
    def logger(self, logger):
        self.__logger = logger

    def set_asyncronous(self, asyncr):
        self.__asyncronous = asyncr

    def get_pid_file(self):
        return "{}/.{}.pid".format(self.__workspace, self.__task_name)

    def get_task_pid(self):
        try:
            with open(self.get_pid_file(), "r") as f:
                pid = f.readline().strip()
        except Exception:
            return -1

        if pid == "":
            return -1

        return pid

    def _task_is_running(self):
        pid = self.get_task_pid()
        if pid > 0 and os.path.exists("/proc/{}".format(pid)):
            return True
        return False

    @run_in_namespace
    def run(self):

        if self.__asyncronous:
            start = time.time()
            while True:
                if self._task_is_running():
                    break

                if time.time()-start > 10:
                    break

            if not self._task_is_running():
                print "[ {} ] {} fail to start".\
                    format("ERROR", self.__task_name)
                self.__logger.error("[ {} ] {} fail to start".
                                    format("ERROR", self.__task_name))
            else:
                print "[ {:<6} ] {} is running".format(self.get_task_pid(), self.__task_name)
                self.__logger.info("[ {:<6} ] {} is running".
                                   format(self.get_task_pid(), self.__task_name))
            return

        cmdline = self.get_commandline()

        self.__logger.info("{}'s command line: {}".
                           format(self.__task_name, cmdline))

        pid_file = self.get_pid_file()

        if self._task_is_running():
            print "[ {:<6} ] {} is already running".format(
                self.get_task_pid(), self.__task_name)
            self.__logger.info("[ {:<6} ] {} is already running".
                               format(self.get_task_pid(), self.__task_name))
            return
        elif os.path.exists(pid_file):
            # If the qemu quits exceptionally when starts, pid file is also
            # created, but actually the qemu died.
            os.remove(pid_file)

        pid = self.execute_command(cmdline, self.__logger, log_path=self.__log_path)

        print "[ {:<6} ] {} starts to run".format(pid, self.__task_name)
        self.__logger.info("[ {:<6} ] {} starts to run".format(pid, self.__task_name))

        with open(pid_file, "w") as f:
            if os.path.exists("/proc/{}".format(pid)):
                f.write("{}".format(pid))

    def terminate(self):
        task_pid = self.get_task_pid()
        pid_file = self.get_pid_file()
        try:
            if task_pid > 0:
                os.kill(int(task_pid), signal.SIGTERM)
                print "[ {:<6} ] {} stop".format(task_pid, self.__task_name)
                self.__logger.info("[ {:<6} ] {} stop".
                                   format(task_pid, self.__task_name))
                time.sleep(1)
                if os.path.exists("/proc/{}".format(task_pid)):
                    os.kill(int(task_pid), signal.SIGKILL)
            else:
                print "[ {:<6} ] {} is stopped".format("", self.__task_name)
                self.__logger.info("[ {:<6} ] {} is stopped".
                                   format("", self.__task_name))

            if os.path.exists(pid_file):
                os.remove(pid_file)
        except OSError:
            if os.path.exists(pid_file):
                os.remove(pid_file)
            if not os.path.exists("/proc/{}".format(task_pid)):
                print "[ {:<6} ] {} is stopped".format(task_pid, self.__task_name)
                self.__logger.info("[ {:<6} ] {} is stopped".
                                   format(task_pid, self.__task_name))
            else:
                print("[ {:<6} ] {} stop failed.".
                      format(task_pid, self.__task_name))
                self.__logger.info("[ {:<6} ] {} stop failed.".
                                   format(task_pid, self.__task_name))

    def status(self):
        task_pid = self.get_task_pid()
        pid_file = "{}/.{}.pid".format(self.__workspace, self.__task_name)
        if not os.path.exists(pid_file):
            print("{} is stopped".format(self.__task_name))
        elif not os.path.exists("/proc/{}".format(task_pid)):
            print("{} is stopped".format(self.__task_name))
            os.remove(pid_file)
        else:
            task_pid = self.get_task_pid()
            if task_pid > 0:
                print "[ {:<6} ] {} is running".\
                    format(task_pid, self.__task_name)

    @staticmethod
    @double_fork
    def execute_command(command, logger, log_path="",):
        args = shlex.split(command)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=False)

        flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        time.sleep(1)

        errout = None
        try:
            errout = proc.stderr.read()
        except IOError:
            pass
        if errout is not None:
            if log_path:
                with open(log_path, 'w') as fp:
                    fp.write(errout)
            else:
                logger.error(errout)

        if not os.path.isdir("/proc/{}".format(proc.pid)):
            logger.exception("command {} run failed".format(command))
            raise CommandRunFailed(command, errout)

        return proc.pid
