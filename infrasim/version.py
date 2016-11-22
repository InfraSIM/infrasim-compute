import os
from yaml_loader import YAMLLoader
import config
from . import ipmi, socat, run_command, qemu

VERSION_CONF = os.path.join(config.infrasim_template, "version.yml")


def version():
    version_str = ""
    qemu_ver_cmd = qemu.get_qemu() + " --version"
    ipmi_ver_cmd = ipmi.get_ipmi() + " -v"
    socat_ver_cmd = socat.get_socat() + " -V"
    version_str += "{:<10}: {}\n".format("Kernel", run_command("uname -sr")[1].split('\n')[0])
    version_str += "{:<10}: {}\n".format("Base OS", run_command("cat /etc/issue")[1].split('\\')[0])
    version_str += "{:<10}: {}\n".format("QEMU", run_command(qemu_ver_cmd)[1].split(',')[0])
    version_str += "{:<10}: {}\n".format("OpenIPMI", run_command(ipmi_ver_cmd)[1].split('\n')[0])
    version_str += "{:<10}: {}\n".format("Socat",
                                        ' '.join(run_command(socat_ver_cmd)[1].split('\n')[1].split(' ')[0:3]))
    with open(VERSION_CONF, 'r') as v_yml:
        version_str += "{:<10}: infrasim-compute version {}\n".format("InfraSIM",
                                                                     YAMLLoader(v_yml).get_data()["version"])
    return version_str
