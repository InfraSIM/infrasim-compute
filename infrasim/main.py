#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import netifaces
from . import ipmi, socat, run_command, qemu
from . import CommandRunFailed, ArgsNotCorrect, has_option, model

INFRASIM_CONF = "/etc/infrasim/infrasim.yml"
VERSION_CONF = "/usr/local/infrasim/template/version.yml"


def infrasim_main(arg):

    with open(INFRASIM_CONF, 'r') as f_yml:
        conf = yaml.load(f_yml)

    eth = ""

    if has_option(conf, "type"):
        node = conf["type"]
    else:
        print "Can't get infrasim type.\n" \
            "Please check infrasim configure file: {}".format(INFRASIM_CONF)
        sys.exit(-1)

    try:
        eth = conf["compute"]["networks"][0]["network_name"]
    except TypeError:
        print "Attribute missing from infrasim node network.\n" \
              "Please check infrasim configure file: {}".format(INFRASIM_CONF)
        sys.exit(-1)
    except KeyError:
        print "Can't get infrasim node network.\n" \
              "Please check infrasim configure file: {}".format(INFRASIM_CONF)
        sys.exit(-1)

    node = model.CNode(conf)

    try:
        if arg == "start":
            node.init()
            node.precheck()
            node.start()
            print "Infrasim service started.\n" \
                "You can access node {} via vnc:{}:5901". \
                format(node.get_node_name(),
                    netifaces.ifaddresses(eth)[netifaces.AF_INET][0]['addr'])
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
            qemu_ver_cmd = qemu.get_qemu() + " --version"
            ipmi_ver_cmd = ipmi.get_ipmi() + " -v"
            socat_ver_cmd = socat.get_socat() + " -V"
            print "Kernel:  ", run_command("uname -sr")[1].split('\n')[0]
            print "Base OS: ", run_command("cat /etc/issue")[1].split('\\')[0]
            print "QEMU:    ", run_command(qemu_ver_cmd)[1].split(',')[0]
            try:
                print "OpenIPMI:", run_command(ipmi_ver_cmd)[1].split('\n')[0]
            except CommandRunFailed as e:
                print str(e.output).split('\n')[0]
            print "Socat:   ", ' '.join(run_command(socat_ver_cmd)[1]. \
                    split('\n')[1].split(' ')[0:3])
            with open(VERSION_CONF, 'r') as v_yml:
                print "InfraSIM: infrasim-compute version", yaml.load(v_yml)["version"]
        else:
            print "{} start|stop|status|restart|version".format(sys.argv[0])
    except CommandRunFailed as e:
        print "{} run failed\n".format(e.value)
        print "Infrasim-main starts failed"
    except ArgsNotCorrect as e:
        print "{} args is incorrect".format(e.value)
        print "infrasim-main starts failed"
