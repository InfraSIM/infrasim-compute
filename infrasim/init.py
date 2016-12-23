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
import config

mac_base = "00:60:16:"


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

    if os.path.exists(config.infrasim_logdir):
        shutil.rmtree(config.infrasim_logdir)
    os.mkdir(config.infrasim_logdir)


def init_infrasim_conf(node_type):

    # Prepare default network
    networks = []
    nics_list = helper.get_all_interfaces()
    eth_nic = filter(lambda x: x != "lo", nics_list)[0]
    mac = create_mac_address()
    networks.append({"nic": eth_nic, "mac": mac})

    # Prepare default disk
    disks = []
    disks.append({"size": 8})

    # Render infrasim.yml
    infrasim_conf = ""
    with open(config.infrasim_config_template, "r") as f:
        infrasim_conf = f.read()
    template = jinja2.Template(infrasim_conf)
    infrasim_conf = template.render(node_type=node_type, disks=disks, networks=networks)
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


def infrasim_init(node_type="quanta_d51", skip_installation=False, target_home=None, config_file=None):
    try:
        create_infrasim_directories()
        if not skip_installation:
            install_packages()
            update_bridge_cfg()
            config_library_link()

        if config_file:
            if os.path.exists(config_file):
                shutil.copy2(config_file, config.infrasim_etc)
            else:
                raise Exception("{} not found.".format(config_file))
        else:
            init_infrasim_conf(node_type)

        get_socat()
        get_ipmi()
        get_qemu()
        print "Infrasim init OK"
    except CommandNotFound as e:
        print "command:{} not found\n" \
              "Infrasim init failed".format(e.value)
    except CommandRunFailed as e:
        print "command:{} run failed\n" \
              "Infrasim init failed".format(e.value)
