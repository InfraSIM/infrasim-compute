'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import time
import signal
import shlex
import subprocess
import fcntl
from infrasim import CommandRunFailed
from infrasim.log import infrasim_log, LoggerType
from infrasim.helper import run_in_namespace, double_fork
from infrasim.filelock import FileLock
from infrasim.colors import icolors


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
        self.checking_time = 1

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

    def bind_cpus_with_policy(self):
        pass

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
        pid = "-1"
        try:
            with open(self.get_pid_file(), "r") as f:
                pid = f.readline().strip()
        except Exception:
            pid = "-1"
        finally:
            pid = "-1" if pid == '' else pid
            return int(pid)

    def __task_is_running(self, pid):
        return pid > 0 and os.path.exists("/proc/{}".format(pid))

    def task_is_running(self, pid=-1):
        pid = self.get_task_pid() if pid < 0 else pid
        return self.__task_is_running(pid)

    def __wait_task_completed(self, lock, pid=-1, timeout=15):
        timeout = timeout - self.checking_time + 1

        start = time.time()
        while True:
            if time.time() - start > timeout:
                break

            if self.task_is_running(pid):
                break

            lock.release()
            time.sleep(0.5)
            lock.acquire()

        # in case the process created, but exit accidently, so
        # check again
        return self.task_is_running(pid)

    def __print_task(self, pid, name, state, color=icolors.GREEN):
        print("{}{}{}".format(icolors.WHITE, "[", icolors.NORMAL), end='')
        print(" {}{:<6}{} ".format(color, pid, icolors.NORMAL), end='')
        print("{}{}{}".format(icolors.WHITE, "]", icolors.NORMAL), end='')
        print(" {} is {}.".format(name, state))

    @run_in_namespace
    def run(self):
        pid_file = self.get_pid_file()
        lock = FileLock("{}.lck".format(pid_file))
        if self.__asyncronous:
            with lock.acquire():
                if self.__wait_task_completed(lock):
                    self.__print_task(self.get_task_pid(), self.__task_name, "running")
                    self.__logger.info("[ {:<6} ] {} is running".format(self.get_task_pid(),
                                                                        self.__task_name))
                    self.bind_cpus()
                else:
                    self.__print_task('  -  ', self.__task_name, "not running", icolors.RED)
            return

        cmdline = self.get_commandline()

        self.__logger.info("{}'s command line: {}".
                           format(self.__task_name, cmdline))

        with lock.acquire():
            if self.task_is_running():
                self.__print_task(self.get_task_pid(), self.__task_name, "running")
                self.__logger.info("[ {:<6} ] {} is already running".format(self.get_task_pid(),
                                                                            self.__task_name))
                return
            elif os.path.exists(pid_file):
                # If the qemu quits exceptionally when starts, pid file is also
                # created, but actually the qemu died.
                os.remove(pid_file)

            pid = self.execute_command(cmdline, self.__logger, log_path=self.__log_path, duration=self.checking_time)

            if self.__wait_task_completed(lock, pid):
                self.__print_task(pid, self.__task_name, "running")
                self.__logger.info("[ {:<6} ] {} starts to run".format(pid, self.__task_name))

                with open(pid_file, "w") as f:
                    if os.path.exists("/proc/{}".format(pid)):
                        f.write("{}".format(pid))

    def terminate(self):
        pid_file = self.get_pid_file()
        lock = FileLock("{}.lck".format(pid_file))
        with lock.acquire():
            task_pid = self.get_task_pid()
            try:
                if self.__task_is_running(task_pid):
                    os.kill(task_pid, signal.SIGTERM)
                    time.sleep(1)
                    if self.__task_is_running(task_pid):
                        os.kill(task_pid, signal.SIGKILL)
                    self.__print_task(task_pid, self.__task_name, "stopped", icolors.RED)
                    self.__logger.info("[ {:<6} ] {} stop".format(task_pid, self.__task_name))
                else:
                    self.__print_task('  -  ', self.__task_name, "stopped", icolors.RED)
                    self.__logger.info("[ {:<6} ] {} is stopped".format("", self.__task_name))

                if os.path.exists(pid_file):
                    os.remove(pid_file)
            except OSError:
                if not self.__task_is_running(task_pid):
                    if os.path.exists(pid_file):
                        os.remove(pid_file)

                    self.__print_task(task_pid, self.__task_name, "stopped", icolors.RED)
                    self.__logger.info("[ {:<6} ] {} is stopped".format(task_pid, self.__task_name))
                else:
                    self.__print_task(task_pid, self.__task_name, "running")
                    self.__logger.info("[ {:<6} ] {} stop failed.".format(task_pid, self.__task_name))

    def status(self):
        pid_file = self.get_pid_file()
        lock = FileLock("{}.lck".format(pid_file))
        with lock.acquire():
            task_pid = self.get_task_pid()
            if not self.__task_is_running(task_pid):
                if os.path.exists(pid_file):
                    os.remove(pid_file)
                self.__print_task('  -  ' if task_pid < 0 else task_pid, self.__task_name, "stopped", icolors.RED)
            else:
                self.__print_task(task_pid, self.__task_name, "running")

    @staticmethod
    @double_fork
    def execute_command(command, logger, log_path="", duration=1):
        args = shlex.split(command)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=False)

        flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        time.sleep(duration)

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

    def bind_cpus(self):
        pass
