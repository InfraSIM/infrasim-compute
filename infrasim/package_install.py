#!/usr/bin/env python
"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""
# -*- coding: utf-8 -*-

"""
this script is used to install the necessary packages before starting infrasim-compute
the packages includes:
    ipmitool libssh-dev libpython-dev libffi-dev libyaml-dev
    infrasim-qemu
    infrasim-openipmi
besides, seabios binary file is also downloaded into expected folder
"""

import requests
import shutil
import os
from infrasim import run_command

BASE_URL = "https://api.bintray.com/packages/infrasim/"


def install_official_packages():
    run_command("apt-get install -y socat ipmitool libssh-dev libffi-dev libyaml-dev")


def install_bintray_packages(repo, package):
    print "downloading " + package + "..."
    download_link = BASE_URL + repo + "/" + package + "/files"
    response = requests.get(download_link)
    data = response.json()
    latest_time = data[0]["created"]
    path = ""
    file_name = ""
    for item in data:
        if item["created"] >= latest_time:
            latest_time = item["created"]
            path = item["path"]
            file_name = item["name"]
    response = requests.get("https://dl.bintray.com/infrasim/" + repo + "/" + path)
    if package is "Seabios":
        file_name = os.path.join("/usr/local/share/qemu/", "bios-256k.bin")
    else:
        file_name = "/tmp/" + file_name
    with open(file_name, "wb") as f:
        for chunk in response.iter_content(8192):
            f.write(chunk)
    if package is not "Seabios":
        print "installing " + package + "..."
        run_command("dpkg -i " + file_name)


def copy_data_to_workspace():
    dst = "{}/.infrasim/data/".format(os.environ["HOME"])
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree("/usr/local/infrasim/data/", dst)


def create_bridge_conf_link():
    if not os.path.exists("/usr/local/etc/qemu/bridge.conf"):
        bridge_conf_initial_dir = "/etc/qemu"
        bridge_conf_dir = "/usr/local/etc/qemu"
        if not os.path.exists(bridge_conf_initial_dir):
            os.makedirs(bridge_conf_initial_dir)
        if not os.path.exists(bridge_conf_dir):
            os.makedirs(bridge_conf_dir)
        os.symlink("/etc/qemu/bridge.conf", "/usr/local/etc/qemu/bridge.conf")


def package_install():
    install_official_packages()
    install_bintray_packages("deb", "Qemu")
    install_bintray_packages("deb", "OpenIpmi")
    install_bintray_packages("generic", "Seabios")
    copy_data_to_workspace()
    create_bridge_conf_link()


