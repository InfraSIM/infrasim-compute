'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
import jinja2
import stat
import shutil
from infrasim import CommandNotFound, ArgsNotCorrect, CommandRunFailed
from infrasim import config, helper
from infrasim import has_option, run_command
from infrasim.helper import run_in_namespace
from infrasim.model.core.task import Task


class CBMC(Task):

    VBMC_TEMP_CONF = os.path.join(config.infrasim_template, "vbmc.conf")

    def __init__(self, bmc_info={}):
        super(CBMC, self).__init__()

        self.__bmc = bmc_info
        self.__address = None
        self.__channel = None
        self.__lan_interface = None
        self.__lancontrol_script = ""
        self.__chassiscontrol_script = ""
        self.__startcmd_script = ""
        self.__oem_file_path = ""
        self.__startnow = "true"
        self.__poweroff_wait = None
        self.__kill_wait = None
        self.__username = None
        self.__password = None
        self.__emu_file = None
        self.__config_file = ""
        self.__bin = "ipmi_sim"
        self.__port_iol = None
        self.__ipmi_listen_range = "::"
        self.__intf_not_exists = False
        self.__intf_no_ip = False

        # Be careful with updating this number, it could cause FRU index confliction
        # on particular platform, e.g. onr FRU of s2600wtt already occupied index 10
        self.__historyfru = 99

        # Node wise attributes
        self.__vendor_type = None
        self.__port_ipmi_console = 9000
        self.__port_qemu_ipmi = 9002
        self.__sol_device = ""
        self.__sol_enabled = True
        self.__node_name = None

    def enable_sol(self, enabled):
        self.__sol_enabled = enabled

    def set_type(self, vendor_type):
        self.__vendor_type = vendor_type

    def set_port_ipmi_console(self, port):
        self.__port_ipmi_console = port

    def set_port_qemu_ipmi(self, port):
        self.__port_qemu_ipmi = port

    def set_sol_device(self, device):
        self.__sol_device = device

    def get_config_file(self):
        return self.__config_file

    def set_config_file(self, dst):
        self.__config_file = dst

    def get_emu_file(self):
        return self.__emu_file

    def set_emu_file(self, path):
        self.__emu_file = path

    def set_node_name(self, node_name):
        self.__node_name = node_name

    @run_in_namespace
    def precheck(self):
        # check if ipmi_sim exists
        try:
            run_command("which {}".format(self.__bin))
        except CommandRunFailed:
            self.logger.exception("[BMC] Cannot find {}".format(self.__bin))
            raise CommandNotFound(self.__bin)

        # check script exits
        if not os.path.exists(self.__lancontrol_script):
            raise ArgsNotCorrect("[BMC] Lan control script {} doesn\'t exist".
                                 format(self.__lancontrol_script))

        if not os.path.exists(self.__chassiscontrol_script):
            raise ArgsNotCorrect("[BMC] Chassis control script {} doesn\'t exist".
                                 format(self.__chassiscontrol_script))

        if not os.path.exists(self.__startcmd_script):
            raise ArgsNotCorrect("[BMC] startcmd script {} doesn\'t exist".
                                 format(self.__startcmd_script))

        if not os.path.exists(self.__oem_file_path):
            raise ArgsNotCorrect("[BMC] oem file path {} doesn\'t exist".
                                 format(self.__oem_file_path))

        # check if self.__port_qemu_ipmi in use
        if helper.check_if_port_in_use("0.0.0.0", self.__port_qemu_ipmi):
            raise ArgsNotCorrect("[BMC] Port {} is already in use.".
                                 format(self.__port_qemu_ipmi))

        if helper.check_if_port_in_use("0.0.0.0", self.__port_ipmi_console):
            raise ArgsNotCorrect("[BMC] Port {} is already in use.".
                                 format(self.__port_ipmi_console))

        # check lan interface exists
        if self.__lan_interface not in helper.get_all_interfaces():
            self.logger.warning("[BMC] Specified BMC interface {} doesn\'t exist.".
                                format(self.__lan_interface))

        # check if lan interface has IP address
        elif not self.__ipmi_listen_range:
            self.logger.warning("[BMC] No IP is found on BMC interface {}.".
                                format(self.__lan_interface))

        # check attribute
        if self.__poweroff_wait < 0:
            raise ArgsNotCorrect("[BMC] poweroff_wait is expected to be >= 0, "
                                 "it's set to {} now".
                                 format(self.__poweroff_wait))

        if type(self.__poweroff_wait) is not int:
            raise ArgsNotCorrect("[BMC] poweroff_wait is expected to be integer, "
                                 "it's set to {} now".
                                 format(self.__poweroff_wait))

        if self.__kill_wait < 0:
            raise ArgsNotCorrect("[BMC] kill_wait is expected to be >= 0, "
                                 "it's set to {} now".
                                 format(self.__kill_wait))

        if type(self.__kill_wait) is not int:
            raise ArgsNotCorrect("[BMC] kill_wait is expected to be integer, "
                                 "it's set to {} now".
                                 format(self.__kill_wait))

        if self.__port_iol < 0:
            raise ArgsNotCorrect("[BMC] Port for IOL(IPMI over LAN) is expected "
                                 "to be >= 0, it's set to {} now".
                                 format(self.__port_iol))

        if type(self.__port_iol) is not int:
            raise ArgsNotCorrect("[BMC] Port for IOL(IPMI over LAN) is expected "
                                 "to be integer, it's set to {} now".
                                 format(self.__port_iol))

        if self.__historyfru < 0:
            raise ArgsNotCorrect("[BMC] History FRU is expected to be >= 0, "
                                 "it's set to {} now".
                                 format(self.__historyfru))

        if type(self.__historyfru) is not int:
            raise ArgsNotCorrect("[BMC] History FRU is expected to be integer, "
                                 "it's set to {} now".
                                 format(self.__historyfru))

        # check configuration file exists
        if not os.path.isfile(self.__emu_file):
            raise ArgsNotCorrect("[BMC] Target emulation file doesn't exist: {}".
                                 format(self.__emu_file))

        if not os.path.isfile(self.__config_file):
            raise ArgsNotCorrect("[BMC] Target config file doesn't exist: {}".
                                 format(self.__config_file))

    def __render_template(self):
        for target in ["startcmd", "stopcmd", "resetcmd"]:
            if not has_option(self.__bmc, target):
                src = os.path.join(config.infrasim_template, target)
                dst = os.path.join(self.get_workspace(), "script", target)
                with open(src, "r")as f:
                    src_text = f.read()
                template = jinja2.Template(src_text)
                dst_text = template.render(
                    yml_file=os.path.join(self.get_workspace(),
                                          "etc/infrasim.yml")
                )
                with open(dst, "w") as f:
                    f.write(dst_text)
                os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        if not has_option(self.__bmc, "startcmd"):
            self.__startcmd_script = os.path.join(self.get_workspace(),
                                                  "script", "startcmd")

        if not has_option(self.__bmc, "chassiscontrol"):
            path_startcmd = os.path.join(self.get_workspace(),
                                         "script/startcmd")
            path_stopcmd = os.path.join(self.get_workspace(),
                                        "script/stopcmd")
            path_resetcmd = os.path.join(self.get_workspace(),
                                         "script/resetcmd")
            path_bootdev = os.path.join(self.get_workspace(), "bootdev")
            path_qemu_pid = os.path.join(self.get_workspace(),
                                         ".{}-node.pid".format(self.__node_name))
            src = os.path.join(config.infrasim_template, "chassiscontrol")
            dst = os.path.join(self.get_workspace(),
                               "script/chassiscontrol")
            with open(src, "r") as f:
                src_text = f.read()
            template = jinja2.Template(src_text)
            dst_text = template.render(startcmd=path_startcmd,
                                       stopcmd=path_stopcmd,
                                       resetcmd=path_resetcmd,
                                       qemu_pid_file=path_qemu_pid,
                                       bootdev=path_bootdev)
            with open(dst, "w") as f:
                f.write(dst_text)
            os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            self.__chassiscontrol_script = dst

        if not has_option(self.__bmc, "lancontrol"):
            shutil.copy(os.path.join(config.infrasim_template, "lancontrol"),
                        os.path.join(self.get_workspace(),
                                     "script", "lancontrol"))

            self.__lancontrol_script = os.path.join(self.get_workspace(),
                                                    "script", "lancontrol")

    def write_bmc_config(self, dst=None):
        if dst is None:
            dst = self.__config_file
        else:
            self.__config_file = dst

        # Render vbmc.conf
        bmc_conf = ""
        with open(self.__class__.VBMC_TEMP_CONF, "r") as f:
            bmc_conf = f.read()
        template = jinja2.Template(bmc_conf)
        bmc_conf = template.render(startcmd_script=self.__startcmd_script,
                                   oem_file_path=self.__oem_file_path,
                                   lan_channel=self.__channel,
                                   chassis_control_script=self.__chassiscontrol_script,
                                   lan_control_script=self.__lancontrol_script,
                                   intf_not_exists=self.__intf_not_exists,
                                   intf_no_ip=self.__intf_no_ip,
                                   lan_interface=self.__lan_interface,
                                   ipmi_listen_range=self.__ipmi_listen_range,
                                   username=self.__username,
                                   password=self.__password,
                                   port_qemu_ipmi=self.__port_qemu_ipmi,
                                   port_ipmi_console=self.__port_ipmi_console,
                                   port_iol=self.__port_iol,
                                   sol_device=self.__sol_device,
                                   poweroff_wait=self.__poweroff_wait,
                                   kill_wait=self.__kill_wait,
                                   startnow=self.__startnow,
                                   historyfru=self.__historyfru,
                                   sol_enabled=self.__sol_enabled)

        with open(dst, "w") as f:
            f.write(bmc_conf)

    @run_in_namespace
    def init(self):
        self.__address = self.__bmc.get('address', 0x20)
        self.__channel = self.__bmc.get('channel', 1)

        if 'interface' in self.__bmc:
            self.__lan_interface = self.__bmc['interface']
            self.__ipmi_listen_range = helper.get_interface_ip(self.__lan_interface)
            if self.__lan_interface not in helper.get_all_interfaces():
                self.__intf_not_exists = True
            elif not self.__ipmi_listen_range:
                self.__intf_no_ip = True
        else:
            nics_list = helper.get_all_interfaces()
            self.__lan_interface = filter(lambda x: x != "lo", nics_list)[0]

        if 'lancontrol' in self.__bmc:
            self.__lancontrol_script = self.__bmc['lancontrol']
        elif self.get_workspace():
            self.__lancontrol_script = os.path.join(self.get_workspace(),
                                                    "script",
                                                    "lancontrol")
        else:
            self.__lancontrol_script = os.path.join(config.infrasim_template,
                                                    "lancontrol")

        if 'chassiscontrol' in self.__bmc:
            self.__chassiscontrol_script = self.__bmc['chassiscontrol']
        elif self.get_workspace():
            self.__chassiscontrol_script = os.path.join(self.get_workspace(),
                                                        "script",
                                                        "chassiscontrol")

        if 'startcmd' in self.__bmc:
            self.__startcmd_script = self.__bmc['startcmd']
        elif self.get_workspace():
            self.__startcmd_script = os.path.join(self.get_workspace(),
                                                  "script",
                                                  "startcmd")

        if 'oem_file_path' in self.__bmc:
            self.__oem_file_path = self.__bmc['oem_file_path']
        elif self.get_workspace():
            self.__oem_file_path = os.path.join(self.get_workspace(),
                                                  "data")

        if self.__bmc.get("startnow") is False:
            self.__startnow = "false"

        self.__poweroff_wait = self.__bmc.get('poweroff_wait', 5)
        self.__kill_wait = self.__bmc.get('kill_wait', 1)
        self.__username = self.__bmc.get('username', "admin")
        self.__password = self.__bmc.get('password', "admin")
        self.__port_iol = self.__bmc.get('ipmi_over_lan_port', 623)
        self.__historyfru = self.__bmc.get('historyfru', 99)

        if 'emu_file' in self.__bmc:
            self.__emu_file = self.__bmc['emu_file']
        elif self.get_workspace():
            self.__emu_file = os.path.join(self.get_workspace(),
                                           "data/{}.emu".format(self.__vendor_type))
        else:
            self.__emu_file = os.path.join(config.infrasim_data,
                                           "{0}/{0}.emu".format(self.__vendor_type))

        if self.__sol_device:
            pass
        elif self.get_workspace():
            self.__sol_device = os.path.join(self.get_workspace(), ".pty0")
        else:
            self.__sol_device = os.path.join(config.infrasim_etc, "pty0")

        if 'config_file' in self.__bmc:
            self.__config_file = self.__bmc['config_file']
            if os.path.exists(self.__config_file):
                shutil.copy(self.__config_file,
                            os.path.join(self.get_workspace(), "etc/vbmc.conf"))
        elif self.get_workspace() and not self._task_is_running():
            # render template
            self.__render_template()
            self.write_bmc_config(os.path.join(self.get_workspace(), "etc/vbmc.conf"))
        elif os.path.exists(os.path.join(self.get_workspace(), "etc/vbmc.conf")):
            self.__config_file = os.path.join(self.get_workspace(), "etc/vbmc.conf")
        else:
            raise ArgsNotCorrect("[BMC] Couldn't find vbmc.conf")

    def get_commandline(self):
        path = os.path.join(self.get_workspace(), "data")
        ipmi_cmd_str = "{0} -c {1} -f {2} -n -s {3}" .\
            format(self.__bin, self.__config_file, self.__emu_file, path)

        return ipmi_cmd_str
