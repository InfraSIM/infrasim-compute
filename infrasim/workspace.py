import os
import yaml
import shutil
import jinja2
import stat
import config
import model
from yaml_loader import YAMLLoader
from . import has_option, InfraSimError


class Workspace(object):
    """
    This class uses CNode's information to initiate its instance.
    It creates or update the node's workspace.
    """

    @staticmethod
    def check_workspace_exists(node_name):
        return os.path.exists(os.path.join(config.infrasim_home, node_name))

    @staticmethod
    def get_node_info_in_workspace(node_name):
        node_yml_path = os.path.join(config.infrasim_home,
                                     node_name,
                                     "data",
                                     "infrasim.yml")
        node_info = None
        try:
            with open(node_yml_path, 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
        except:
            raise InfraSimError("Fail to read node {} information from runtime workspace".
                                format(node_name))

        if not isinstance(node_info, dict):
            raise InfraSimError("Node {} information in runtime workspace is invalid".
                                format(node_name))
        return node_info

    def __init__(self, node_info):
        self.__node_info = node_info
        self.__workspace_name = node_info["name"]
        self.__workspace = os.path.join(config.infrasim_home, node_info["name"])

    def get_workspace(self):
        return self.__workspace

    def init(self):
        """
        Create workspace: <HOME>/.infrasim/<node_name>
        .infrasim/<node_name>    # Root folder
            data                 # Data folder
                infrasim.yml     # Save runtime infrasim.yml
                vbmc.conf        # Render template with data from infrasim.yml
                vbmc.emu         # Emulation data
                bios.bin         # BIOS
            script               # Script folder
                chassiscontrol
                lancontrol
                startcmd
                stopcmd
                resetcmd
            .pty0                # Serial device, created by socat, not here
            .<node_name>-socat   # pid file of socat
            .<node_name>-ipmi    # pid file of ipmi
            .<node_name>-qemu    # pid file of qemu
        What's done here:
            I. Create workspace
            II. Create log folder
            III. Create sub folder
            IV. Save infrasim.yml
            V. Render vbmc.conf, render scripts
            VI. Move emulation data, update identifiers, e.g. S/N
            VII. Move bios.bin
        """
        if os.path.exists(self.__workspace):
            shutil.rmtree(self.__workspace)

        # I. Create workspace
        os.mkdir(self.__workspace)
        # II. Create log folder
        path_log = "/var/log/infrasim/{}".format(self.__workspace_name)
        if not os.path.exists(path_log):
            os.mkdir(path_log)

        # III. Create sub folder
        os.mkdir(os.path.join(self.__workspace, "data"))
        os.mkdir(os.path.join(self.__workspace, "script"))

        # IV. Save infrasim.yml
        yml_file = os.path.join(self.__workspace, "data", "infrasim.yml")
        # self.update_node_configuration(self.__node)
        with open(yml_file, 'w') as fp:
            yaml.dump(self.__node_info, fp, default_flow_style=False)

        # V. Render vbmc.conf
        # and prepare bmc scripts
        if has_option(self.__node_info, "bmc", "config_file"):
            shutil.copy(self.__node_info["bmc"]["config_file"],
                        os.path.join(self.__workspace, "data", "vbmc.conf"))
        else:
            bmc_obj = model.CBMC(self.__node_info.get("bmc", {}))

            # Render sctipts: startcmd, stopcmd, resetcmd, chassiscontrol
            # Copy scripts: lancontrol

            for target in ["startcmd", "stopcmd", "resetcmd"]:
                if not has_option(self.__node_info, "bmc", target):
                    src = os.path.join(config.infrasim_template, target)
                    dst = os.path.join(self.__workspace, "script", target)
                    with open(src, "r")as f:
                        src_text = f.read()
                    template = jinja2.Template(src_text)
                    dst_text = template.render(yml_file=yml_file)
                    with open(dst, "w") as f:
                        f.write(dst_text)
                    os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            if not has_option(self.__node_info, "bmc", "startcmd"):
                path_startcmd = os.path.join(self.__workspace,
                                             "script",
                                             "startcmd")
                bmc_obj.set_startcmd_script(path_startcmd)

            if not has_option(self.__node_info, "bmc", "chassiscontrol"):
                path_startcmd = os.path.join(self.__workspace,
                                             "script",
                                             "startcmd")
                path_stopcmd = os.path.join(self.__workspace,
                                            "script",
                                            "stopcmd")
                path_resetcmd = os.path.join(self.__workspace,
                                             "script",
                                             "resetcmd")
                path_bootdev = os.path.join(self.__workspace,
                                            "", "bootdev")
                path_qemu_pid = os.path.join(self.__workspace,
                                             ".{}-node.pid".
                                             format(self.__workspace_name))
                src = os.path.join(config.infrasim_template, "chassiscontrol")
                dst = os.path.join(self.__workspace, "script", "chassiscontrol")
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

                path_chassiscontrol = dst
                bmc_obj.set_chassiscontrol_script(path_chassiscontrol)

            if not has_option(self.__node_info, "bmc", "lancontrol"):
                os.symlink(os.path.join(config.infrasim_template,
                                        "lancontrol"),
                           os.path.join(self.__workspace,
                                        "script",
                                        "lancontrol"))

                path_lancontrol = os.path.join(self.__workspace,
                                               "script",
                                               "lancontrol")
                bmc_obj.set_lancontrol_script(path_lancontrol)

            # Render connection port/device
            if has_option(self.__node_info, "type"):
                bmc_obj.set_type(self.__node_info["type"])

            if has_option(self.__node_info, "sol_device"):
                bmc_obj.set_sol_device(self.__node_info["sol_device"])

            if has_option(self.__node_info, "ipmi_console_port"):
                bmc_obj.set_port_ipmi_console(self.__node_info["ipmi_console_port"])

            if has_option(self.__node_info, "bmc_connection_port"):
                bmc_obj.set_port_qemu_ipmi(self.__node_info["bmc_connection_port"])

            if has_option(self.__node_info, "sol_enable"):
                bmc_obj.enable_sol(self.__node_info["sol_enable"])

            bmc_obj.set_workspace(self.__workspace)
            bmc_obj.netns = self.__node_info.get("namespace")
            bmc_obj.init()
            bmc_obj.write_bmc_config(os.path.join(self.__workspace,
                                                  "data",
                                                  "vbmc.conf"))

        # VI. Move emulation data
        # Update identifier accordingly
        path_emu_dst = os.path.join(self.__workspace, "data")
        if has_option(self.__node_info, "bmc", "emu_file"):
            shutil.copy(self.__node_info["bmc"]["emu_file"], path_emu_dst)
        else:
            node_type = self.__node_info["type"]
            path_emu_src = os.path.join(config.infrasim_data, "{0}/{0}.emu".format(node_type))
            shutil.copy(path_emu_src, os.path.join(path_emu_dst, "{}.emu".
                                                   format(node_type)))

        # VII. Move bios.bin
        path_bios_dst = os.path.join(self.__workspace, "data")
        if has_option(self.__node_info, "compute", "smbios"):
            shutil.copy(self.__node_info["compute"]["smbios"], path_bios_dst)
        else:
            node_type = self.__node_info["type"]
            path_bios_src = os.path.join(config.infrasim_data,
                                         "{0}/{0}_smbios.bin".format(node_type))
            shutil.copy(path_bios_src, os.path.join(path_emu_dst,
                                                    "{}_smbios.bin".
                                                    format(node_type)))
            # Place holder to sync serial number

    def terminate(self):
        """
        Destroy node's workspace if it exists
        """
        os.system("rm -rf {}".format(self.__workspace))
