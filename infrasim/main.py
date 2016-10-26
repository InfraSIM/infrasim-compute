import os
import sys
from yaml_loader import YAMLLoader
import netifaces
from netifaces import interfaces, ifaddresses, AF_INET
import config
from . import ipmi, socat, run_command, qemu
from . import CommandRunFailed, ArgsNotCorrect, model

VERSION_CONF = os.path.join(config.infrasim_template, "version.yml")

def version():
    version_str = ""
    qemu_ver_cmd = qemu.get_qemu() + " --version"
    ipmi_ver_cmd = ipmi.get_ipmi() + " -v"
    socat_ver_cmd = socat.get_socat() + " -V"
    version_str += "Kernel:  {}\n".format(run_command("uname -sr")[1].split('\n')[0])
    version_str += "Base OS: {}\n".format(run_command("cat /etc/issue")[1].split('\\')[0])
    version_str += "QEMU:    {}\n".format(run_command(qemu_ver_cmd)[1].split(',')[0])
    try:
        version_str += "OpenIPMI:   {}\n".format(run_command(ipmi_ver_cmd)[1].split('\n')[0])
    except CommandRunFailed as e:
        print str(e.output).split('\n')[0]
    version_str += "Socat:   {}\n".format(' '.join(run_command(socat_ver_cmd)[1].
                                split('\n')[1].split(' ')[0:3]))
    with open(VERSION_CONF, 'r') as v_yml:
        version_str += "InfraSIM: infrasim-compute version {}\n".format(YAMLLoader(v_yml).get_data()["version"])
    return version_str


def ip4_addresses():
    ip_list = []
    for interface in netifaces.interfaces():
        for link in netifaces.ifaddresses(interface).get(AF_INET, ()):
            ip_list.append(link['addr'])
    return ip_list


def infrasim_main(arg):

    with open(config.infrasim_initial_config, 'r') as f_yml:
        node_info = YAMLLoader(f_yml).get_data()

    node = model.CNode(node_info)

    try:
        if arg == "start":
            node.init()
            node.precheck()
            node.start()
            # get IP address
            ifname = node_info["compute"]["networks"][0]["network_name"]
            print "Infrasim service started.\n" \
                  "Node {} graphic interface accessible via: \n" \
                  "VNC port: 5901 \n" \
                  "Either host IP: {} \n" \
                  "depending on host in which network VNC viewer is running". \
                  format(node.get_node_name(), ip4_addresses())

        elif arg == "stop":
            node.init()
            node.stop()
            node.terminate_workspace()
            print "Infrasim Service stopped"
        elif arg == "status":
            node.init()
            node.status()
        elif arg == "restart":
            node.init()
            node.stop()
            print "Restart InfraSIM service..."
            node.precheck()
            node.start()
        elif arg == "version":
            print version()
        else:
            print "{} start|stop|status|restart|version".format(sys.argv[0])
    except CommandRunFailed as e:
        print "{} run failed\n".format(e.value)
        print "Infrasim-main starts failed"
        node.init()
        node.stop()
        node.terminate_workspace()
    except ArgsNotCorrect as e:
        print "{} args is incorrect".format(e.value)
        print "infrasim-main starts failed"
        node.init()
        node.stop()
        node.terminate_workspace()
