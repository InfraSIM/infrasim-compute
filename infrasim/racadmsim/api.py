#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import jinja2
import os
from os import linesep
from infrasim import config
from infrasim.repl import REPL, register, parse, QuitREPL
from . import env
from . import model


j2_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                    os.path.join(config.infrasim_template, "racadmsim"),
                    followlinks=True
                ),
                trim_blocks=True,
                lstrip_blocks=True
            )


def fake_data(name):
    if not env.racadm_data:
        return None
    data_path = os.path.join(env.racadm_data, name)
    if os.path.exists(data_path):
        with open(data_path) as fp:
            rsp = linesep.join(fp.read().splitlines())
        return rsp
    else:
        return None


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
            topo_embedded, topo_backplane = model.get_drive_topology()
            t = j2_tmpl.render(satadom=topo_embedded[0], mapping=topo_backplane)
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
            j2_tmpl = j2_env.get_template("hwinventory_storage.j2")
            topo_embedded, topo_backplane = model.get_drive_topology()
            t_storage = j2_tmpl.render(satadom=topo_embedded[0], mapping=topo_backplane)

            j2_hwinventory_tmpl = j2_env.from_string(fake_data("hwinventory"))
            t_hwinventory = j2_hwinventory_tmpl.render(storage=t_storage)

            return t_hwinventory

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
            env.logger_r.info("[req][repl] {}".format(inp))

            try:
                out = self.do(cmd)
            except EOFError:
                env.logger_r.warning("[rsp][repl] EOFError")
                return
            except QuitREPL:
                env.logger_r.info("[rsp][repl] Quite REPL")
                return


            # PRINT
            self.output(linesep)
            self.output(" ".join(["racadm"]+cmd))
            env.logger_r.info("[rsp][repl]{}{}".format(linesep, out))
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
            env.logger_r.info("[req][inline] {}".format(" ".join(args)))
            racadm = RacadmConsole()
            racadm.set_output(self.output)
            racadm_cmd = parse(" ".join(args[1:]))
            rsp = racadm.do(racadm_cmd)
            env.logger_r.info("[rsp][inline]{}{}".format(linesep, rsp))
            if rsp:
                racadm.output(rsp.strip(linesep))
            else:
                racadm.output(linesep)
