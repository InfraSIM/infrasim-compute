"""
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
"""

import requests
import os
import hashlib
from infrasim import run_command, CommandRunFailed

"""
this script is used to install the necessary packages before starting infrasim-compute
the packages includes:
    ipmitool libssh-dev libpython-dev libffi-dev libyaml-dev
    infrasim-qemu
    infrasim-openipmi
besides, seabios binary file is also downloaded into expected folder
"""


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
    sha256 = ""
    for item in data:
        if item["created"] >= latest_time:
            latest_time = item["created"]
            path = item["path"]
            file_name = item["name"]
            sha256 = item["sha256"]
    response = requests.get(
        "https://dl.bintray.com/infrasim/" + repo + "/" + path)
    if not response:
        raise Exception("Failed to fetch package {} from bintray.\n"
                        "response code is {}".format(package, response))
    if not len(response.content):
        raise Exception("Failed to fetch package {} from bintray.\n"
                        "Length of file is zero.".format(package))
    if package is "Seabios":
        file_name = os.path.join("/usr/local/share/qemu/", "bios-256k.bin")
    else:
        file_name = "/tmp/" + file_name
    with open(file_name, "wb") as f:
        for chunk in response.iter_content(8192):
            f.write(chunk)
    if hashlib.sha256(open(file_name, "rb").read()).hexdigest() != sha256:
        raise Exception(
            "The file {} downloaded is not complete, please try again!")
    if package is not "Seabios":
        print "installing " + package + "..."
        run_command("dpkg -i " + file_name)

def check_package(package = "Qemu", cmd = "which qemu-system-x86_64"):
    ''' Return True if Package needs to install'''
    install_package = False
    # Check if package installed
    try:
        qemu_installed = run_command(cmd)
    except CommandRunFailed:
        install_package = True
    else:
        while True:
            ans = raw_input(package+" already exists. Overwrite it? (Y/n)")
            if ans.lower() not in ('yes', 'no', 'y', 'n'):
                print("Sorry, I didn't understand that.")
                continue
            else:
                break
        if ans.lower() in ('yes', 'y'):
            install_package = True

    return install_package

def package_install():
    install_official_packages()

    install_qemu = check_package("Qemu", "which qemu-system-x86_64")
    install_openipmi = check_package("Openipmi", "which ipmi_sim")
    install_seabios = check_package("Seabios", "ls /usr/local/share/qemu/bios-256k.bin")
    if install_qemu:
        install_bintray_packages("deb", "Qemu")
    if install_openipmi:
        install_bintray_packages("deb", "OpenIpmi")
    if install_seabios:
        install_bintray_packages("generic", "Seabios")
