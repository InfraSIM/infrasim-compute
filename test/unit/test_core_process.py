'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
from infrasim import qemu
from infrasim import ipmi
from infrasim import socat
from infrasim import model
from infrasim import config
from test import fixtures
import time
import os
import shutil
import yaml

"""
Test InfraSIM core component:
    - QEMU
    - ipmi
    - ...
Check:
    - binary exist
    - corresponding process can be started by start service
    - corresponding process can be ended by stop service
"""

conf = None
tmp_conf_file = "/tmp/test.yml"


def setUp():
    global conf
    fake_config = fixtures.FakeConfig()
    conf = fake_config.get_node_info()
    node = model.CNode(conf)
    node.set_node_name(conf['name'])
    with open(tmp_conf_file, "w") as f:
        yaml.dump(conf, f, default_flow_style=False)


def tearDown():
    global conf
    workspace = "{}/{}".format(config.infrasim_home, conf['name'])
    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    if os.path.exists(tmp_conf_file):
        os.unlink(tmp_conf_file)

    conf = None


def test_qemu_exist():
    try:
        qemu.get_qemu()
        assert True
    except:
        assert False


def test_ipmi_exist():
    try:
        ipmi.get_ipmi()
        assert True
    except:
        assert False


def test_socat_exist():
    try:
        socat.get_socat()
        assert True
    except:
        assert False


def test_socat_process_start():
    try:
        socat.start_socat(conf_file=tmp_conf_file)
        time.sleep(2)
        socat.status_socat()
        assert True
    except:
        assert False


def test_ipmi_process_start():
    try:
        ipmi.start_ipmi(conf_file=tmp_conf_file)
        time.sleep(2)
        ipmi.status_ipmi()
        assert True
    except:
        assert False


def test_qemu_process_start():
    try:
        qemu.status_qemu()
        assert True
    except:
        assert False


def test_qemu_process_status_running():
    try:
        qemu.status_qemu()
        assert True
    except:
        assert False


def test_ipmi_process_status_running():
    try:
        ipmi.status_ipmi()
        assert True
    except:
        assert False


def test_socat_process_status_running():
    try:
        socat.status_socat()
        assert True
    except:
        assert False


def test_qemu_prcess_stop():
    try:
        qemu.stop_qemu(conf_file=tmp_conf_file)
        qemu.status_qemu()
        assert False
    except:
        assert True


def test_ipmi_process_stop():
    try:
        ipmi.stop_ipmi(conf_file=tmp_conf_file)
        ipmi.status_ipmi()
        assert False
    except:
        assert True


def test_socat_process_stop():
    try:
        socat.stop_socat(conf_file=tmp_conf_file)
        socat.status_socat()
        assert False
    except:
        assert True
