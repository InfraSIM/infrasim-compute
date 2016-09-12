#!/bin/bash
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

# this script is used to install the necessary packages before starting infrasim-compute
# the packages includes:
#     ipmitool libssh-dev libpython-dev libffi-dev libyaml-dev 
#     infrasim-qemu
#     infrasim-openipmi
#
# besides, seabios binary file is also downloaded into expected folder


openipmi_link="https://bintray.com/infrasim/deb/download_file?file_path=pool%2Fmain%2FO%2FOpenIpmi%2Finfrasim-openipmi_2.0.22-1.0.9ubuntu16.04_amd64.deb"
qemu_link="https://bintray.com/infrasim/deb/download_file?file_path=pool%2Fmain%2FQ%2FQemu%2Finfrasim-qemu_2.6.0-1.0.8ubuntu16.04_amd64.deb"
seabios_link="https://bintray.com/infrasim/generic/download_file?file_path=infrasim-seabios_1.0-5ubuntu16.04_amd64.bin"
seabios_file="bios-256k.bin"

fail()
{
    [ -d deb ] && rm -rf deb
    echo $1
    exit 1
}
    
# install the packages with "apt-get install"
sudo apt-get install -y socat ipmitool libssh-dev libffi-dev libyaml-dev
[ $? != 0 ] && fail "sudo apt-get install -y socat ipmitool libssh-dev libffi-dev libyaml-dev fails"

# remove original packages
dpkg -r infrasim-qemu
dpkg -r infrasim-openipmi

# download and install the packages with "dpkg"
pushd ~
[ -d deb ] && rm -rf deb
mkdir deb
pushd deb

wget ${openipmi_link} -O openipmi.deb -q
[ -f openipmi.deb ] || fail "can't download openipmi package from bintray"
wget ${qemu_link} -O qemu.deb -q
[ -f qemu.deb ] || fail "can't download qemu package from bintray"

dpkg -i qemu.deb
qemu_path=`which qemu-system-x86_64`
[ -n ${qemu_path} ] || fail "failed to install qemu"

dpkg -i openipmi.deb
openipmi_path=`which ipmi_sim`
[ -n ${openipmi_path} ] || fail "failed to install openipmi"
popd

[ -d deb ] && rm -rf deb
popd

pushd "/usr/local/share/qemu/"
[ -f ${seabios_file} ] && rm -f ${seabios_file}
wget ${seabios_link} -O ${seabios_file} -q
[ -f ${seabios_file} ] || fail "can't download seabios file"
popd
