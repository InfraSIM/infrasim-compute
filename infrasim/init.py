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
import netifaces
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

    if os.path.exists(config.infrasim_intermediate_data):
        shutil.rmtree(config.infrasim_intermediate_data)
    os.mkdir(config.infrasim_intermediate_data)

    if os.path.exists(config.infrasim_intermediate_etc):
        shutil.rmtree(config.infrasim_intermediate_etc)
    os.mkdir(config.infrasim_intermediate_etc)

    if os.path.exists(config.infrasim_logdir):
        shutil.rmtree(config.infrasim_logdir)
    os.mkdir(config.infrasim_logdir)

    if not os.path.exists("/usr/local/libexec"):
        os.mkdir("/usr/local/libexec")


def init_infrasim_conf():

    # Prepare default network
    networks = []
    nics_list = netifaces.interfaces()
    eth_nic = filter(lambda x: 'e' in x, nics_list)[0]
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
    infrasim_conf = template.render(disks=disks, networks=networks)
    with open(config.infrasim_initial_config, "w") as f:
        f.write(infrasim_conf)


def install_packages():
    package_install()


def config_library_link():
    run_command("ldconfig")


def update_bridge_cfg():
    run_command('echo "allow br0" > /etc/qemu/bridge.conf')


def infrasim_init():
    try:
        create_infrasim_directories()
        install_packages()
        init_infrasim_conf()
        config_library_link()
        update_bridge_cfg()
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
