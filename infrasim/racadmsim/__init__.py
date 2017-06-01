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
import os
import logging
import jinja2
from os import linesep
from infrasim import sshim
from infrasim.repl import REPL, register, parse, QuitREPL
from infrasim.yaml_loader import YAMLLoader


auth_map = {}
racadm_data = None
r_log = None
node_name = None
node_info = None
j2_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                    os.path.join(config.infrasim_template, "racadmsim"),
                    followlinks=True
                ),
                trim_blocks=True,
                lstrip_blocks=True
            )

def auth(username, password):
    global auth_map
    if username in auth_map and auth_map[username] == password:
        return paramiko.AUTH_SUCCESSFUL
    else:
        return paramiko.AUTH_FAILED


def fake_data(name):
    global racadm_data
    if not racadm_data:
        return None
    data_path = os.path.join(racadm_data, name)
    if os.path.exists(data_path):
        with open(data_path) as fp:
            rsp = linesep.join(fp.read().splitlines())
        return rsp
    else:
        return None


def init_log():
    """
    Create log folder, prepare handler and recording level
    """
    global node_name
    global r_log

    r_log = logging.getLogger(__name__)

    log_folder = os.path.join(config.infrasim_logdir, node_name)
    if not os.path.exists(log_folder):
        os.mkdir(log_folder)
    log_path = os.path.join(log_folder, "racadmsim.log")

    r_hdl = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    r_hdl.setFormatter(formatter)
    r_log.addHandler(r_hdl)
    r_log.setLevel(logging.NOTSET)


def get_node_info():
    """
    Get runtime node information
    """
    global node_name

    runtime_yml_path = os.path.join(config.infrasim_home,
                                    node_name, "etc", "infrasim.yml")
    with open(runtime_yml_path, 'r') as fp:
        node_info = YAMLLoader(fp).get_data()

    return node_info


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
    def getled(self, ctx, args):
        """
        [RACADM] get led status
        """
        return fake_data("getled")

    @register
    def getsysinfo(self, ctx, args):
        """
        [RACADM] get system info
        """
        return fake_data("getsysinfo")

    @register
    def storage(self, ctx, args):
        """
        [RACADM] get storage information
        """
        if args == ["storage", "get", "pdisks", "-o"]:
            j2_tmpl = j2_env.get_template("storage.j2")
            node_info = get_node_info()

            d = node_info["compute"]["storage_backend"][0]["drives"][0]

            scsi_drives = node_info["compute"]["storage_backend"][1]["drives"]

            t = j2_tmpl.render(satadom = d, drives = scsi_drives)

            return t
        else:
            return None

    @register
    def get(self, ctx, args):
        """
        [RACADM] get device information
        """
        if args == ["get", "BIOS"]:
            return fake_data("get_bios")
        elif args == ["get", "BIOS.MemSettings"]:
            return fake_data("get_bios_mem_setting")
        elif args == ["get", "IDRAC"]:
            return fake_data("get_idrac")
        elif args == ["get", "LifeCycleController"]:
            return fake_data("get_life_cycle_controller")
        elif args == ["get", "LifeCycleController.LCAttributes"]:
            return fake_data("get_life_cycle_controller_lc_attributes")
        else:
            return None

    @register
    def hwinventory(self, ctx, args):
        """
        [RACADM] hwinventory
        """
        if args == ["hwinventory"]:
            return fake_data("hwinventory")
        elif args == ["hwinventory", "nic"]:
            return fake_data("hwinventory_nic")
        elif args == ["hwinventory", "nic.Integrated.1-1-1"]:
            return fake_data("hwinventory_nic_integrated_1-1-1")
        elif args == ["hwinventory", "nic.Integrated.1-2-1"]:
            return fake_data("hwinventory_nic_integrated_1-2-1")
        elif args == ["hwinventory", "nic.Integrated.1-3-1"]:
            return fake_data("hwinventory_nic_integrated_1-3-1")
        elif args == ["hwinventory", "nic.Integrated.1-4-1"]:
            return fake_data("hwinventory_nic_integrated_1-4-1")
        else:
            return None

    @register
    def setled(self, ctx, args):
        """
        [RACADM] set led status
        """
        if args == ["setled", "-l", "0"]:
            return fake_data("setled_l_0")
        else:
            return None

    def run(self):
        self.welcome()
        while True:
            # READ
            inp = self.input(self.prompt)

            # EVAL
            cmd = self.refine_cmd(parse(inp))
            logger_r.info("[req][repl] {}".format(inp))

            try:
                out = self.do(cmd)
            except EOFError:
                logger_r.warning("[rsp][repl] EOFError")
                return
            except QuitREPL:
                logger_r.info("[rsp][repl] Quite REPL")
                return

            # PRINT
            self.output(linesep)
            self.output(" ".join(["racadm"]+cmd))
            logger_r.info("[rsp][repl]{}{}".format(linesep, out))
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
            logger_r.info("[req][inline] {}".format(" ".join(args)))
            racadm = RacadmConsole()
            racadm.set_output(self.output)
            racadm_cmd = parse(" ".join(args[1:]))
            rsp = racadm.do(racadm_cmd)
            logger_r.info("[rsp][inline]{}{}".format(linesep, rsp))
            if rsp:
                racadm.output(rsp.strip(linesep))
            else:
                racadm.output(linesep)


class iDRACHandler(sshim.Handler):
    def __init__(self, server, connection):
        # paramiko.ServerInterface.start_server() raise exception
        # and make server instance quite.
        # Here the exception is captured in case of a service stop
        try:
            super(iDRACHandler, self).__init__(server, connection)
        except Exception:
            pass

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
            if cmds == ["racadm"]:
                channel.send("SSH to iDRAC {}:{} then go to racadmsim console.{}".
                             format(self.address, self.server.port, linesep))
            # else, execute command and response
            else:
                idrac = iDRACConsole()
                idrac.set_output(channel.sendall)
                rsp = idrac.do(cmds)
                idrac.output(rsp)

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
        logger_r.info("command rev: {}".format(groups['cmd']))
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
          password="admin",
          data_src="auto"):
    # Init environment
    global auth_map
    global racadm_data
    global node_name

    auth_map[username] = password
    node_name = instance
    if os.path.exists(data_src):
        racadm_data = data_src
    init_log()

    server = sshim.Server(iDRACServer,
                          logger=logger_r,
                          address=ipaddr,
                          port=int(port),
                          handler=iDRACHandler)
    logger.info("{}-racadm start on ip: {}, port: {}".
                format(node_name, ipaddr, port))
    server.run()

if __name__ == "__main__":
    # Try to run this from code root directory, with command:
    #     python -m infrasim.racadmsim
    auth_map["admin"] = "admin"
    node_name = "default"
    init_log()

    auth_map["admin"] = "admin"
    server = sshim.Server(iDRACServer, logger=logger_r, port=10022, handler=iDRACHandler)
    server.run()
