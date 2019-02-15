import os
import yaml
import shutil
from infrasim import config
import subprocess
from yaml_loader import YAMLLoader
from . import has_option, InfraSimError, set_option


class Workspace(object):
    """
    This class uses CNode's information to initiate its instance.
    It creates or update the node's workspace.
    """

    @staticmethod
    def check_workspace_exists(node_name):
        if node_name is None:
            raise InfraSimError("chassis name is mandatory")
        return os.path.exists(os.path.join(config.infrasim_home, node_name))

    @staticmethod
    def get_node_info_in_workspace(node_name):
        node_yml_path = os.path.join(config.infrasim_home, node_name,
                                     "etc/infrasim.yml")
        node_info = None
        try:
            with open(node_yml_path, 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
        except Exception:
            raise InfraSimError("Fail to read node {} information from runtime workspace".
                                format(node_name))

        if not isinstance(node_info, dict):
            raise InfraSimError("Node {} information in runtime workspace is invalid".
                                format(node_name))
        return node_info

    @staticmethod
    def check_node(node_name):
        return os.path.exists(os.path.join(config.infrasim_home, node_name, "etc", "infrasim.yml"))

    def __init__(self, node_info):
        self._info = node_info
        self._workspace_name = node_info["name"]
        self._workspace = os.path.join(config.infrasim_home, node_info["name"])

    def get_workspace(self):
        return self._workspace

    def init(self):
        """
        Create workspace: <HOME>/.infrasim/<node_name>
        .infrasim/<node_name>        # root folder
            etc/
                infrasim.yml         # save runtime infrasim.yml
                vbmc.conf            # render template with data from infrasim.yml
            data/                    # data folder
                vbmc.emu             # emulation data
                bios.bin             # BIOS
                ipmi_sim/            # ipmi_sim runtime, managed by ipmi_sim
                    sdr              # runtime sdr
                    sel              # runtime sel
            script/                  # script folder
                chassiscontrol
                lancontrol
                setbootcmd
                startcmd
                stopcmd
                resetcmd
            sda.img (sdb.img, etc)   # drive for nodes
            .serial                  # unix socket file to forward serial data, managed by socat
            .pty0                    # serial device, managed by socat
            .<node_name>-socat       # pid file of socat
            .<node_name>-ipmi        # pid file of ipmi
            .<node_name>-qemu        # pid file of qemu
            .<node_name>-racadm      # pid file of RACADM simulation
        What's done here:
            I. Create workspace
            II. Create log folder
            III. Create sub folder
            IV. Save infrasim.yml
            V. Render vbmc.conf, render scripts
            VI. Move emulation data, update identifiers, e.g. S/N
            VII. Move bios.bin
        """
        if not os.path.exists(self._workspace):
            os.mkdir(self._workspace)

        # II. Create log folder
        path_log = os.path.join(config.infrasim_log_dir, self._workspace_name)
        if not os.path.exists(path_log):
            os.mkdir(path_log)

        # III. Create sub folder
        data_path = os.path.join(self._workspace, "data")
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        script_path = os.path.join(self._workspace, "scripts")
        if not os.path.exists(script_path):
            os.mkdir(script_path)

        etc_path = os.path.join(self._workspace, "etc")
        if not os.path.exists(etc_path):
            os.mkdir(etc_path)

        node_type = self._info["type"]
        # IV. Move emulation data
        # Update identifier accordingly
        path_data_dst = os.path.join(self._workspace, "data")
        src = dst = os.path.join(path_data_dst, "{0}.emu".format(node_type))
        if has_option(self._info, "bmc", "emu_file"):
            src = self._info["bmc"]["emu_file"]
        elif not os.path.exists(dst):
            src = os.path.join(config.infrasim_data, "{0}/{0}.emu".format(node_type))

        if os.path.dirname(src) != path_data_dst:
            shutil.copy(src, dst)

        set_option(self._info, "bmc", "emu_file", dst)

        # V. Move bios.bin
        src = dst = os.path.join(path_data_dst, "{0}_smbios.bin".format(node_type))
        if has_option(self._info, "compute", "smbios", "file"):
            src = self._info["compute"]["smbios"]["file"]
        elif has_option(self._info, "compute", "smbios") and isinstance(self._info["compute"]["smbios"], str):
            # compatible with previous version.
            src = self._info["compute"]["smbios"]
        elif not os.path.exists(dst):
            src = os.path.join(config.infrasim_data, "{0}/{0}_smbios.bin".format(node_type))

        if os.path.dirname(src) != path_data_dst:
            shutil.copy(src, dst)

        set_option(self._info["compute"], "smbios", "file", dst)

        # VI. Move OEM data and script
        path_oem_file_src = os.path.join(config.infrasim_data, "oem_data.json")
        path_oem_script_src = os.path.join(config.infrasim_scripts, "ipmi_exec.py")
        if os.path.exists(path_oem_file_src):
            shutil.copy(path_oem_file_src, os.path.join(path_data_dst, "oem_data.json"))
        if os.path.exists(path_oem_script_src):
            shutil.copy(path_oem_script_src, os.path.join(script_path, "ipmi_exec.py"))

        # VII. Save infrasim.yml
        yml_file = os.path.join(self._workspace, "etc/infrasim.yml")
        with open(yml_file, 'w') as fp:
            yaml.dump(self._info, fp, default_flow_style=False)

    def terminate(self):
        """
        Destroy node's workspace if it exists
        """
        os.system("rm -rf {}".format(self._workspace))


class ChassisWorkspace(Workspace):
    """
    This class uses CNode's information to initiate its instance.
    It creates or update the node's workspace.
    """

    @staticmethod
    def get_chassis_info_in_workspace(chassis_name):
        chassis_yml_path = os.path.join(config.infrasim_home, chassis_name,
                                        "etc/chassis.yml")
        chassis_info = None
        try:
            with open(chassis_yml_path, 'r') as fp:
                chassis_info = YAMLLoader(fp).get_data()
        except Exception:
            raise InfraSimError("Fail to read node {} information from runtime workspace".
                                format(chassis_name))

        if not isinstance(chassis_info, dict):
            raise InfraSimError("Node {} information in runtime workspace is invalid".
                                format(chassis_name))
        return chassis_info

    def __init__(self, chassis_info):
        super(ChassisWorkspace, self).__init__(chassis_info)

    def get_workspace_data(self):
        return os.path.join(self._workspace, "data")

    def init(self):
        """
        Create chassis workspace: <HOME>/.infrasim/<chassis_name>
        .infrasim/<chassis_name>     # root folder
            chassis.yml
            data/
                drive.bin
                sdr.bin
                smbios.bin
            .<chassis_name>.pid


        What's done here:
            I. Create workspace
            II. Create log folder

        """
        if not os.path.exists(self._workspace):
            os.mkdir(self._workspace)

        # II. Create log folder
        path_log = os.path.join(config.infrasim_log_dir, self._workspace_name)
        if not os.path.exists(path_log):
            os.mkdir(path_log)

        # III. Create sub folder
        data_path = self.get_workspace_data()
        if not os.path.exists(data_path):
            os.mkdir(data_path)

        etc_path = os.path.join(self._workspace, "etc")
        if not os.path.exists(etc_path):
            os.mkdir(etc_path)

        # IV. Save chassis.yml
        yml_file = os.path.join(self._workspace, "etc/chassis.yml")
        with open(yml_file, 'w') as fp:
            yaml.dump(self._info, fp, default_flow_style=False)

        # V. Move emulation data from system folder
        path_oem_file_src = os.path.join(config.infrasim_data, "oem_data.json")
        path_oem_file_dst = os.path.join(data_path, "oem_data.json")
        if os.path.exists(path_oem_file_src) and (os.path.exists(path_oem_file_dst) is False):
            shutil.copy(path_oem_file_src, path_oem_file_dst)

        # VI. Create soft link to sub nodes.
        for node in self._info.get("nodes", []):
            if not os.path.exists(os.path.join(self._workspace, node["name"])):
                subprocess.call(["ln", "-s", "{}/{}".format(config.infrasim_home, node["name"]), self._workspace])
