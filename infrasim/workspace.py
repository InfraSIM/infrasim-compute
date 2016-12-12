import os
import yaml
import shutil
import config
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
        node_yml_path = os.path.join(config.infrasim_home, node_name,
                                     "etc/infrasim.yml")
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
        os.mkdir(os.path.join(self.__workspace, "etc"))

        # IV. Save infrasim.yml
        yml_file = os.path.join(self.__workspace, "etc/infrasim.yml")
        with open(yml_file, 'w') as fp:
            yaml.dump(self.__node_info, fp, default_flow_style=False)

        # V. Move emulation data
        # Update identifier accordingly
        path_emu_dst = os.path.join(self.__workspace, "data")
        if has_option(self.__node_info, "bmc", "emu_file"):
            shutil.copy(self.__node_info["bmc"]["emu_file"], path_emu_dst)
        else:
            node_type = self.__node_info["type"]
            path_emu_src = os.path.join(config.infrasim_data, "{0}/{0}.emu".format(node_type))
            shutil.copy(path_emu_src, os.path.join(path_emu_dst, "{}.emu".
                                                   format(node_type)))

        # VI. Move bios.bin
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
