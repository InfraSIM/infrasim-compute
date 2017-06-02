import os
import jinja2
import random
import string
import shutil
from infrasim import run_command, CommandNotFound, CommandRunFailed
from infrasim.socat import get_socat
from infrasim.ipmi import get_ipmi
from infrasim.qemu import get_qemu
from infrasim.package_install import package_install
from infrasim import helper
from infrasim import WorkspaceExisting
import config
import subprocess
from .log import infrasim_log, LoggerType, infrasim_logdir
from .version import version
from infrasim.yaml_loader import YAMLLoader
from .config import infrasim_default_config

mac_base = "00:60:16:"
logger_env = infrasim_log.get_logger(LoggerType.environment.value)

def create_mac_address():
    macs = []
    for i in range(0, 3):
        macs.append(''.join(random.SystemRandom().choice("abcdef" + string.digits) for _ in range(2)))
    return mac_base + ":".join([macs[0], macs[1], macs[2]])


def create_infrasim_directories():
    if os.path.exists(config.infrasim_home):
        shutil.rmtree(config.infrasim_home)
    os.mkdir(config.infrasim_home)
    os.mkdir(config.infrasim_node_config_map)

    if os.path.exists(infrasim_logdir):
        shutil.rmtree(infrasim_logdir)
    os.mkdir(infrasim_logdir)


def init_infrasim_conf(node_type):

    splash_path = os.path.join(config.get_infrasim_root(), "data/boot_logo.jpg")
    # Prepare default network
    networks = []
    nics_list = helper.get_all_interfaces()
    eth_nic = filter(lambda x: x != "lo", nics_list)[0]
    mac = create_mac_address()
    networks.append({"nic": eth_nic, "mac": mac})

    # create_infrasim_directories
    if not os.path.exists(config.infrasim_home):
        os.mkdir(config.infrasim_home)
        os.mkdir(config.infrasim_node_config_map)

    # create_infrasim_log_directories
    if not os.path.exists(infrasim_logdir):
        os.mkdir(infrasim_logdir)

    # Prepare default disk
    disks = []
    disks.append({"size": 8})

    # Render infrasim.yml
    infrasim_conf = ""
    with open(config.infrasim_config_template, "r") as f:
        infrasim_conf = f.read()
    template = jinja2.Template(infrasim_conf)
    infrasim_conf = template.render(node_type=node_type, disks=disks, networks=networks, splash_path=splash_path)
    with open(config.infrasim_default_config, "w") as f:
        f.write(infrasim_conf)


def install_packages():
    package_install()


def config_library_link():
    run_command("ldconfig")


def update_bridge_cfg():
    qemu_sys_prefix = os.path.dirname(get_qemu()).replace('bin', '')
    bridge_conf_loc = os.path.join(qemu_sys_prefix, "etc/qemu")
    if not os.path.exists(bridge_conf_loc):
        os.mkdir(bridge_conf_loc)
    bridge_conf = os.path.join(qemu_sys_prefix, bridge_conf_loc, "bridge.conf")
    with open(bridge_conf, "w") as f:
        f.write("allow all")

def destroy_existing_nodes():
    nodes = os.listdir(config.infrasim_home)
    if os.path.exists(config.infrasim_node_config_map):
        nodes.remove('.node_map')
    for node in nodes:
        os.system("infrasim node destroy {}".format(node))

def check_existing_workspace():
    if os.path.exists(config.infrasim_home):
        nodes = os.listdir(config.infrasim_home)
        if len(nodes) > 1:
            return True
        else:
            return False

def get_environment():
    cpu_info = run_command('lscpu')
    logger_env.info("cpu information: \n{}".
                    format(cpu_info[1]))
    version_info = version()
    logger_env.info("infrasim version information: \n{}".
                    format(version_info))
    try:
        with open(infrasim_default_config, 'r') as fp:
            node_info = YAMLLoader(fp).get_data()
            logger_env.info("infrasim default configuration "
                            "information: \n{}\n".
                            format(node_info))
    except:
        pass


def infrasim_init(node_type="dell_r730", skip_installation=True, force=False, target_home=None, config_file=None):
    if check_existing_workspace():
        if not force:
            raise WorkspaceExisting("There is node workspace existing.\n"
                                    "If you want to remove it, please run:\n"
                                    "\"infrasim init -f \"")

        if force:
            destroy_existing_nodes()
            create_infrasim_directories()

    if not skip_installation:
        install_packages()
        config_library_link()
        update_bridge_cfg()

    if config_file:
        if os.path.exists(config_file):
            shutil.copy2(config_file, config.infrasim_etc)
        else:
            raise Exception("{} not found.".format(config_file))
    else:
        init_infrasim_conf(node_type)

    # record infrasim environment
    get_environment()

    get_socat()
    get_ipmi()
    get_qemu()
