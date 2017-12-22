'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

import os
import unittest
import yaml
import re
import shutil
import struct
from infrasim import ArgsNotCorrect
from infrasim import model
from infrasim import socat
from infrasim import config
from infrasim import helper
from test import fixtures
from nose.tools import raises
from glob import *


TMP_CONF_FILE = "/tmp/test.yml"
FW_CFG_DIR = "/tmp/data"


class qemu_functions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        img_files = glob(config.infrasim_home+"/*.img")
        for img_file in img_files:
            os.unlink(img_file)

        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        cls.node = model.CNode(node_info)
        cls.node.init()
        cls.node.terminate_workspace()

    def test_set_cpu(self):
        try:
            cpu_info = {
                "quantities": 2,
                "type": "Haswell"
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-cpu Haswell" in cpu.get_option()
            assert "-smp 2" in cpu.get_option()
        except:
            assert False

    def test_set_cpu_no_info(self):
        try:
            cpu_info = {}

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-cpu host" in cpu.get_option()
            assert "-smp 2" in cpu.get_option()
        except:
            assert False

    def test_set_cpu_only_quantity(self):
        try:
            cpu_info = {
                "quantities": 8
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-smp 8,sockets=2,cores=4,threads=1" in cpu.get_option()
        except:
            assert False

    def test_set_cpu_negative_quantity(self):
        try:
            cpu_info = {
                "quantities": -2
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
        except ArgsNotCorrect:
            assert True
        else:
            assert False

    def test_set_cpu_feature_nx(self):
        try:
            cpu_info = {
                "features": "+nx"
            }

            cpu = model.CCPU(cpu_info)
            cpu.init()
            cpu.precheck()
            cpu.handle_parms()
            assert "-cpu host,+nx" in cpu.get_option()
        except:
            assert False

    def test_set_menu_unsupported_type_digit(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        node_info["compute"]["boot"]["menu"] = 1
        node = model.CNode(node_info)
        node.init()
        try:
            node.precheck()
        except ArgsNotCorrect, e:
            assert "The 'menu' must be either 'on' or 'off'" in e.value

    def test_set_menu_unsupported_string_value(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        node_info["compute"]["boot"]["menu"] = "any_string"
        node = model.CNode(node_info)
        node.init()
        try:
            node.precheck()
        except ArgsNotCorrect, e:
            assert "The 'menu' must be either 'on' or 'off'" in e.value

    def test_set_menu_legal_value(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["boot"]["menu"] = "on"
        compute = model.CCompute(compute_info)
        compute.set_workspace("{}/{}".format(config.infrasim_home, node_info["name"]))
        compute.init()

        assert "menu=on" in compute.get_commandline()

    def test_set_ahci_storage_controller(self):
        try:
            backend_storage_info = [{
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8, "file": "/tmp/sda.img"}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device ahci" in storage.get_option()
        except:
            assert False

    def test_set_nvme_controller(self):
        try:
            backend_storage_info = [{
                "type": "nvme",
                "cmb_size": 256,
                "serial": "26E0A024T2VD",
                "drives": [{"size": 8}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device nvme" in storage.get_option()
        except:
            assert False

    def test_set_nvme_controller_default_serial(self):
        try:
            backend_storage_info = [{
                "type": "nvme",
                "cmb_size": 256,
                "drives": [{"size": 8}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            p = re.compile(r"-device nvme,serial=\w+,cmb_size_mb=256,drive=nvme-0,id=dev-nvme-0")
            m = p.search(storage.get_option())
            assert m is not None
        except:
            assert False

    def test_set_nvme_controller_default_cmb_size(self):
        try:
            backend_storage_info = [{
                "type": "nvme",
                "serial": "26E0A024T2VD",
                "drives": [{"size": 8}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device nvme" in storage.get_option()
            assert "cmb_size_mb=256" in storage.get_option()
        except:
            assert False

    def test_set_nvme_controller_invalid_cmb_size(self):
        try:
            backend_storage_info = [{
                "type": "nvme",
                "cmb_size": 255,
                "drives": [{"size": 8}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
        except ArgsNotCorrect as e:
            assert "CMB size" in e.value
        else:
            assert False

    def test_set_lsi_storage_controller(self):
        try:
            backend_storage_info = [{
                "type": "lsi",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8, "file": "/tmp/sda.img"}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device lsi" in storage.get_option()
        except:
            assert False

    def test_set_megasas_storage_controller(self):
        try:
            backend_storage_info = [{
                "type": "megasas",
                "max_drive_per_controller": 6,
                "use_jbod": True,
                "msi": True,
                "max_cmds": 1024,
                "max_sge": 128,
                "sas_address": "000abc",
                "drives": [{"size": 8, "file": "/tmp/sda.img"}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device megasas" in storage.get_option()
            assert "use_jbod=True" in storage.get_option()
            assert "msi=True" in storage.get_option()
            assert "max_cmds=1024" in storage.get_option()
            assert "max_sge=128" in storage.get_option()
            assert "sas_address=000abc" in storage.get_option()
        except:
            assert False

    @raises(ArgsNotCorrect)
    def test_unsupported_storage_controller(self):
        backend_storage_info = [{
            "type": "scsi",
            "max_drive_per_controller": 8,
            "drives": [{"size": 8, "file": "/tmp/sda.img"}]
        }]
        storage = model.CBackendStorage(backend_storage_info)
        storage.init()
        storage.precheck()
        storage.handle_parms()
        assert "-device scsi" in storage.get_option()

    def test_set_ahci_storage_controller_2x(self):
        try:
            backend_storage_info = [{
                "type": "ahci",
                "max_drive_per_controller": 2,
                "drives": [{"size": 8, "file": "/tmp/sda.img"},
                           {"size": 8, "file": "/tmp/sdb.img"},
                           {"size": 8, "file": "/tmp/sdc.img"}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "sata1.0" in storage.get_option()
        except:
            assert False

    def test_set_ahci_drive_model(self):
        try:
            backend_storage_info = [{
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [{"size": 8,
                            "model": "SATADOM",
                            "file": "/tmp/sda.img"}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "SATADOM" in storage.get_option()
        except:
            assert False

    def test_set_ahci_drive_serial(self):
        try:
            backend_storage_info = [{
                "type": "ahci",
                "max_drive_per_controller": 6,
                "drives": [
                    {"size": 8, "file": "/tmp/sda.img",
                     "model": "SATADOM", "serial": "HUSMM442"}
                ]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "HUSMM442" in storage.get_option()
        except:
            assert False

    def test_set_scsi_drive_vender(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [
                    {"size": 8, "serial": "HUSMM442", "file": "/tmp/sda.img",
                        "model": "SATADOM", "vendor": "Hitachi"}],
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "Hitachi" in storage.get_option()
        except:
            assert False

    def test_set_scsi_drive_rotation(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8, "model": "SATADOM",
                    "serial": "HUSMM442", "vendor": "Hitachi",
                    "rotation": 1, "file": "/tmp/sda.img"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "rotation" in storage.get_option()
        except:
            assert False

    def test_set_scsi_drive_product(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                        "size": 8, "model": "SATADOM", "file": "/tmp/sda.img",
                        "serial": "HUSMM442", "vendor": "Hitachi",
                        "rotation": 1, "product": "Quanta"}]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "product" in storage.get_option()
        except:
            assert False

    def test_set_scsi_drive_port_index(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "port_index": "1"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "port_index=1" in storage.get_option()
        except:
            assert False

    def test_set_scsi_drive_port_wwn(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "port_wwn": "wwn-000abc"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "port_wwn=wwn-000abc" in storage.get_option()
        except:
            assert False

    def test_set_scsi_drive_channel(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "channel": "1"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "channel=1" in storage.get_option()
        except:
            assert False

    def test_set_scsi_scsiid(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "scsi-id": "1"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "scsi-id=1" in storage.get_option()
        except:
            assert False

    def test_set_scsi_lun(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "lun": "1"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "lun=1" in storage.get_option()
        except:
            assert False

    def test_set_scsi_slot(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "slot_number": "2"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "slot_number=2" in storage.get_option()
        except:
            assert False

    def test_set_drive_page_file_exist(self):
        file_name = "/tmp/an_avaiable_page_file.bin"
        os.system("touch {0}".format(file_name))
        ps = r"-device \S+page_file={0}[\s,]".format(file_name)
        p = re.compile(ps)
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8, "model": "SATADOM",
                    "serial": "HUSMM442", "vendor": "Hitachi",
                    "rotation": 1, "file": "/tmp/sda.img",
                    "page-file": file_name
                }]
            }]

            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            m = p.search(storage.get_option())
            assert m is not None
        except Exception, e:
            assert False
        finally:
            os.system("rm -f {0}".format(file_name))

    def test_set_drive_page_file_not_exist(self):
        file_name = "/tmp/an_avaiable_page_file.bin"
        os.system("rm -f {0}".format(file_name))

        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8, "model": "SATADOM",
                    "serial": "HUSMM442", "vendor": "Hitachi",
                    "rotation": 1, "file": "/tmp/sda.img",
                    "page-file": file_name
                }]
            }]

            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()

        except ArgsNotCorrect, e:
            assert "page file {0} doesnot exist".format(file_name) in e.value
        except:
            assert False

    def test_enable_drive_share_rw(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "share-rw": True
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "share-rw=True" in storage.get_option()
        except:
            assert False

    def test_disable_drive_share_rw(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "share-rw": False
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "share-rw" not in storage.get_option()
        except:
            assert False

    def test_fault_drive_share_rw(self):
        try:
            backend_storage_info = [{
                "type": "megasas-gen2",
                "max_drive_per_controller": 6,
                "drives": [{
                    "size": 8,
                    "file": "/tmp/sda.img",
                    "share-rw": "fake"
                }]
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
        except ArgsNotCorrect as e:
            assert "share-rw is not boolean" in e.value

    def test_set_smbios(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["smbios"] = "/tmp/test.smbios"

        compute_info["smbios"] = "/tmp/test.smbios"
        compute = model.CCompute(compute_info)
        compute.set_workspace("{}/{}".format(config.infrasim_home,
                                             node_info['name']))
        compute.init()
        assert compute.get_smbios() == "/tmp/test.smbios"

    def test_set_smbios_without_workspace(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            compute_info = yaml.load(f_yml)["compute"]

        compute = model.CCompute(compute_info)
        compute.set_type("s2600kp")
        compute.init()
        assert compute.get_smbios() == \
            "{}/s2600kp/s2600kp_smbios.bin".format(config.infrasim_data)

    def test_set_smbios_with_type_and_workspace(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]

        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_type("s2600kp")
        compute.set_workspace(workspace)
        compute.init()
        assert compute.get_smbios() == os.path.join(workspace,
                                                    "data",
                                                    "s2600kp_smbios.bin")

    def test_set_extra_option(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["extra_option"] = "-msg timestamp=on"
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "msg timestamp=on" in compute.get_commandline()

    def test_chardev_correct_backend(self):
        chardev_info = {
            "backend": "socket",
            "server": "on",
            "wait": "off",
            "path": "/tmp/monitor.sock"
        }
        chardev = model.CCharDev(chardev_info)
        chardev.init()
        chardev.precheck()
        chardev.handle_parms()
        assert "-chardev socket" in chardev.get_option()

    @raises(ArgsNotCorrect)
    def test_chardev_empty_backend(self):
        chardev_info = {
            "backend": "",
            "server": "on",
            "wait": "off",
            "path": "/tmp/monitor.sock"
        }
        chardev = model.CCharDev(chardev_info)
        chardev.init()
        chardev.precheck()

    @raises(ArgsNotCorrect)
    def test_chardev_none_backend(self):
        chardev_info = {
            "server": "on",
            "wait": "off",
            "path": "/tmp/monitor.sock"
        }
        chardev = model.CCharDev(chardev_info)
        chardev.init()
        chardev.precheck()

    def test_monitor_auto_complete_control_mode_1(self):
        monitor_info = {
            "mode": "control"
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        monitor.precheck()
        monitor.handle_parms()
        assert "-mon chardev" in monitor.get_option()
        assert "mode=control" in monitor.get_option()
        assert "-chardev socket" in monitor.get_option()
        assert "server" in monitor.get_option()
        assert "nowait" in monitor.get_option()
        assert "path={}".format(os.path.join(config.infrasim_etc, ".monitor")) in monitor.get_option()

    def test_monitor_auto_complete_control_mode_2(self):
        monitor_info = {
            "mode": "control",
            "chardev": {}
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        monitor.precheck()
        monitor.handle_parms()
        assert "-mon chardev" in monitor.get_option()
        assert "mode=control" in monitor.get_option()
        assert "-chardev socket" in monitor.get_option()
        assert "server" in monitor.get_option()
        assert "nowait" in monitor.get_option()
        assert "path={}".format(os.path.join(config.infrasim_etc, ".monitor")) in monitor.get_option()

    def test_monitor_auto_complete_readline_mode_1(self):
        monitor_info = {
            "mode": "readline"
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        monitor.precheck()
        monitor.handle_parms()
        assert "-mon chardev" in monitor.get_option()
        assert "mode=readline" in monitor.get_option()
        assert "-chardev socket" in monitor.get_option()
        assert "server" in monitor.get_option()
        assert "nowait" in monitor.get_option()
        assert "host=127.0.0.1" in monitor.get_option()
        assert "port=2345" in monitor.get_option()

    def test_monitor_auto_complete_readline_mode_2(self):
        monitor_info = {
            "mode": "readline",
            "chardev": {}
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        monitor.precheck()
        monitor.handle_parms()
        assert "-mon chardev" in monitor.get_option()
        assert "mode=readline" in monitor.get_option()
        assert "-chardev socket" in monitor.get_option()
        assert "server" in monitor.get_option()
        assert "nowait" in monitor.get_option()
        assert "host=127.0.0.1" in monitor.get_option()
        assert "port=2345" in monitor.get_option()

    def test_monitor_fault_mode(self):
        monitor_info = {
            "mode": "fault"
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor mode: fault" in e.value

    def test_monitor_fault_backend_in_control_mode(self):
        monitor_info = {
            "mode": "control",
            "chardev": {
                "backend": "file"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor chardev backend: file" in e.value

    def test_monitor_fault_backend_in_readline_mode(self):
        monitor_info = {
            "mode": "readline",
            "chardev": {
                "backend": "file"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor chardev backend: file" in e.value

    def test_monitor_fault_server_in_control_mode(self):
        monitor_info = {
            "mode": "control",
            "chardev": {
                "server": "ok"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor chardev server: ok" in e.value

    def test_monitor_fault_server_in_readline_mode(self):
        monitor_info = {
            "mode": "readline",
            "chardev": {
                "server": "ok"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor chardev server: ok" in e.value

    def test_monitor_fault_wait_in_control_mode(self):
        monitor_info = {
            "mode": "control",
            "chardev": {
                "wait": "ok"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor chardev wait: ok" in e.value

    def test_monitor_fault_wait_in_readline_mode(self):
        monitor_info = {
            "mode": "readline",
            "chardev": {
                "wait": "ok"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid monitor chardev wait: ok" in e.value

    def test_monitor_fault_host_in_readline_mode(self):
        monitor_info = {
            "mode": "readline",
            "chardev": {
                "host": "localhost"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Invalid chardev host: localhost" in e.value

    def test_monitor_fault_port_in_readline_mode(self):
        monitor_info = {
            "mode": "readline",
            "chardev": {
                "port": "someport"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Port is not a valid integer: someport" in e.value

    def test_monitor_fault_path_in_control_mode(self):
        monitor_info = {
            "mode": "control",
            "chardev": {
                "path": "/fake/path/.monitor"
            }
        }
        monitor = model.CQemuMonitor(monitor_info)
        monitor.init()
        try:
            monitor.precheck()
        except ArgsNotCorrect, e:
            assert "Path folder doesn't exist: /fake/path" in e.value

    def test_kvm_enabled_yaml_true_env_true(self):
        if not os.path.exists("/dev/kvm"):
            self.skipTest("OS disable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["kvm_enabled"] = True
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "--enable-kvm" in compute.get_commandline()

    def test_kvm_enabled_yaml_true_env_false(self):
        if os.path.exists("/dev/kvm"):
            self.skipTest("OS enable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["kvm_enabled"] = True
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "--enable-kvm" not in compute.get_commandline()

    def test_kvm_enabled_yaml_false_env_true(self):
        if not os.path.exists("/dev/kvm"):
            self.skipTest("OS disable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["kvm_enabled"] = False
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "--enable-kvm" not in compute.get_commandline()

    def test_kvm_enabled_yaml_false_env_false(self):
        if os.path.exists("/dev/kvm"):
            self.skipTest("OS enable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["kvm_enabled"] = False
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "--enable-kvm" not in compute.get_commandline()

    def test_kvm_enabled_yaml_not_defined_env_true(self):
        if not os.path.exists("/dev/kvm"):
            self.skipTest("OS disable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info.pop("kvm_enabled", None)
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "--enable-kvm" in compute.get_commandline()

    def test_kvm_enabled_yaml_not_defined_env_false(self):
        if os.path.exists("/dev/kvm"):
            self.skipTest("OS enable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info.pop("kvm_enabled", None)
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.init()
        compute.handle_parms()
        assert "--enable-kvm" not in compute.get_commandline()

    def test_kvm_enabled_yaml_invalid_env_true(self):
        if not os.path.exists("/dev/kvm"):
            self.skipTest("OS disable KVM, skip")
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        compute_info = node_info["compute"]
        compute_info["kvm_enabled"] = "invalid"
        workspace = "{}/{}".format(config.infrasim_home, node_info['name'])
        compute = model.CCompute(compute_info)
        compute.set_workspace(workspace)
        compute.set_type("dell_r730")
        compute.init()
        compute.set_smbios(os.path.join(config.infrasim_data,
                                        "dell_r730/dell_r730_smbios.bin"))
        try:
            compute.precheck()
        except ArgsNotCorrect, e:
            assert "KVM enabled is not a boolean" in e.value

    @raises(ArgsNotCorrect)
    def test_pcie_rootport_no_chassis_config(self):
        rootport_info = {
            "bus": "pcie.0",
            "slot": 8,
            "device": "ioh3420",
            "id": "rootport1"
        }
        rootport = model.CPCIERootport(rootport_info)
        rootport.init()
        rootport.precheck()
        rootport.handle_parms()

    @raises(ArgsNotCorrect)
    def test_pcie_rootport_no_slot_config(self):
        rootport_info = {
            "bus": "pcie.0",
            "chassis": 1,
            "device": "ioh3420",
            "id": "rootport1"
        }
        rootport = model.CPCIERootport(rootport_info)
        rootport.init()
        rootport.precheck()
        rootport.handle_parms()

    @raises(ArgsNotCorrect)
    def test_pcie_downstream_no_chassis_config(self):
        downstream_info = {
            "bus": "rootport1",
            "slot": 8,
            "device": "xio3130-downstream",
            "id": "downstream1"
        }
        downstream = model.CPCIEDownstream(downstream_info)
        downstream.init()
        downstream.precheck()
        downstream.handle_parms()

    @raises(ArgsNotCorrect)
    def test_pcie_downstream_no_slot_config(self):
        downstream_info = {
            "bus": "rootport1",
            "chassis": 1,
            "device": "xio3130-downstream",
            "id": "downstream1"
        }
        downstream = model.CPCIEDownstream(downstream_info)
        downstream.init()
        downstream.precheck()
        downstream.handle_parms()

    @raises(ArgsNotCorrect)
    def test_pcie_topology_id_duplicated(self):
        pcie_topology = {
            "root_port": [{
                "bus": "pcie.0",
                "chassis": 1,
                "slot": 8,
                "device": "ioh3420",
                "id": "rootport1"
                }],
            "switch": [
                {
                    "downstream":[{
                        "addr": "2.0",
                        "bus" : "upstream1",
                        "slot": 10,
                        "chassis": 1,
                        "device": "xio3130-downstream",
                        "id": "downstream1"
                    },{
                        "addr": "3.0",
                        "bus" : "upstream1",
                        "slot": 11,
                        "chassis": 1,
                        "device": "xio3130-downstream",
                        "id": "downstream1",
                    }],
                    "upstream":[{
                        "bus": "2.0",
                        "device": "x3130-upstream",
                        "id": "upstream1"
                    }]
                }
            ]
        }
        topo = model.CPCIETopology(pcie_topology)
        topo.init()
        topo.precheck()
        topo.handle_parms()

    @raises(AssertionError)
    def test_pcie_fw_cfg_config(self):
        pcie_topology = {
            "root_port": [{
                "addr": "7.0",
                "bus": "pcie.0",
                "chassis": 1,
                "slot": 8,
                "device": "ioh3420",
                "id": "rootport1",
                "pri_bus": 0,
                "sec_bus": 20
                }],
            "switch": [
                {
                    "downstream":[{
                        "addr": "2.0",
                        "bus" : "upstream1",
                        "slot": 10,
                        "chassis": 1,
                        "device": "xio3130-downstream",
                        "id": "downstream1",
                        "pri_bus": 21,
                        "sec_bus": 25
                    },{
                        "addr": "3.0",
                        "bus" : "upstream1",
                        "slot": 11,
                        "chassis": 1,
                        "device": "xio3130-downstream",
                        "id": "downstream2",
                        "pri_bus": 21,
                        "sec_bus": 28
                    }],
                    "upstream":[{
                        "bus": "2.0",
                        "device": "x3130-upstream",
                        "id": "upstream1"
                    }]
                }
            ]
        }
        os.makedirs(FW_CFG_DIR)
        fw_cfg_obj = model.CPCIEFwcfg()
        fw_cfg_obj.set_workspace('/tmp')
        pcie_topology_obj = model.CPCIETopology(pcie_topology)
        pcie_topology_obj.set_fw_cfg_obj(fw_cfg_obj)
        pcie_topology_obj.init()

        fw_cfg_obj.init()
        fw_cfg_obj.precheck()
        fw_cfg_obj.handle_parms()

        cfg = fw_cfg_obj.get_option()
        cfg_file = re.search(r'file=(.+)', cfg)
        cfg_file_path = cfg_file.group(1)
        with open(cfg_file_path, 'rb') as f:
            cfg_lines = f.read()
            cfg_list = []
            for i in range(len(cfg_lines)-1)[::4]:
                tmp_list = cfg_lines[i:i+4]
                cfg_list.append(struct.unpack('HBx', tmp_list))

        yml_cfg_list = []
        rootport_list = [x for x in pcie_topology['root_port']]
        downstream_list = []
        for sw in pcie_topology['switch']:
            for ds in sw['downstream']:
                downstream_list.append(ds)
        for rp in rootport_list + downstream_list:
            pri_bus = rp['pri_bus']
            device, func = rp['addr'].split('.')
            bdf = (int(pri_bus) << 8) + (int(device, 16) << 3) + int(func)
            yml_cfg_list.append((bdf, rp['sec_bus']))
        assert set(yml_cfg_list) != set(cfg_list)


class bmc_configuration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fake_config = fixtures.FakeConfig()
        cls.conf = fake_config.get_node_info()
        cls.WORKSPACE = "{}/{}".format(config.infrasim_home, cls.conf['name'])
        with open(TMP_CONF_FILE, 'w') as f_yml:
            yaml.dump(cls.conf, f_yml, default_flow_style=False)

        cls.node = model.CNode(cls.conf)
        cls.node.set_node_name(cls.conf['name'])
        socat.start_socat(conf_file=TMP_CONF_FILE)

    @classmethod
    def tearDownClass(cls):
        socat.stop_socat(conf_file=TMP_CONF_FILE)
        cls.node = model.CNode(cls.conf)
        cls.node.init()
        cls.node.terminate_workspace()
        if os.path.exists(TMP_CONF_FILE):
            os.unlink(TMP_CONF_FILE)
        if os.path.exists(FW_CFG_DIR):
            shutil.rmtree(FW_CFG_DIR, True)

    def test_set_bmc_type(self):
        bmc = model.CBMC()

        for node_type in ["quanta_d51", "quanta_t41",
                          "dell_r630", "dell_c6320",
                          "s2600kp", "s2600tp", "s2600wtt"]:
            bmc.set_type(node_type)
            bmc.set_workspace(self.__class__.WORKSPACE)
            bmc.init()
            cmd = bmc.get_commandline()
            assert "{0}.emu".format(node_type) \
                   in cmd

    def test_set_bmc_lan_interface(self):
        bmc_info = {
            "interface": "lo"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            for line in fp.readlines():
                if "lan_config_program" in line and "lo" in line:
                    assert True
                    return
            assert False

    def test_set_ipmi_listen_range(self):
        bmc_info = {
            "interface": "lo"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            for line in fp.readlines():
                if "addr 127.0.0.1 623" in line:
                    assert True
                    return
            assert False

    def test_set_fake_bmc_lan_interface(self):
        bmc_info = {
            "interface": "fake_lan"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            print e.value
            assert False
        else:
            assert True

    def test_set_startnow_true(self):
        bmc_info = {
            "startnow": True
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            if "startnow true" in fp.read():
                assert True
            else:
                assert False

    def test_set_startnow_false(self):
        bmc_info = {
            "startnow": False
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            if "startnow false" in fp.read():
                assert True
            else:
                assert False

    def test_set_poweroff_wait(self):
        bmc_info = {
            "poweroff_wait": 0
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            if "poweroff_wait 0" in fp.read():
                assert True
            else:
                assert False

    def test_set_poweroff_wait_negative(self):
        bmc_info = {
            "poweroff_wait": -1
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "poweroff_wait is expected to be >= 0," in str(e)
        else:
            assert False

    def test_set_poweroff_wait_not_int(self):
        bmc_info = {
            "poweroff_wait": "a!"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "poweroff_wait is expected to be integer," in str(e)
        else:
            assert False

    def test_set_historyfru(self):
        bmc_info = {
            "historyfru": 11
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.enable_sol(True)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            if "historyfru=11" in fp.read():
                assert True
            else:
                assert False

    def test_set_historyfru_negative(self):
        bmc_info = {
            "historyfru": -1
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "History FRU is expected to be >= 0," in str(e)
        else:
            assert False

    def test_set_historyfru_not_int(self):
        bmc_info = {
            "historyfru": "a!"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "History FRU is expected to be integer," in str(e)
        else:
            assert False

    def test_set_kill_wait(self):
        bmc_info = {
            "kill_wait": 0
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            if "kill_wait 0" in fp.read():
                assert True
            else:
                assert False

    def test_set_kill_wait_negative(self):
        bmc_info = {
            "kill_wait": -1
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "kill_wait is expected to be >= 0," in str(e)
        else:
            assert False

    def test_set_kill_wait_not_int(self):
        bmc_info = {
            "kill_wait": "a!"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "kill_wait is expected to be integer," in str(e)
        else:
            assert False

    def test_set_username_password(self):
        bmc_info = {
            "username": "test_user",
            "password": "test_password"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        credential = "user 2 true  \"test_user\" \"test_password\" " \
                     "admin    10       none md2 md5 straight"
        with open(bmc.get_config_file(), 'r') as fp:
            if credential in fp.read():
                assert True
            else:
                assert False

    def test_set_another_emu_file(self):
        fn = "/tmp/test_emu"
        os.system("touch {}".format(fn))

        bmc_info = {
            "emu_file": fn
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        assert "-f {}".format(fn) in bmc.get_commandline()
        os.system("rm -rf {}".format(fn))

    def test_set_invalid_emu_file(self):
        fn = "/tmp/emu_test"
        os.system("rm -rf {}".format(fn))

        bmc_info = {
            "emu_file": fn
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "Target emulation file doesn't exist:" in str(e)
        else:
            assert False

    def test_set_another_config_file(self):
        fn = "/tmp/test_conf"
        os.system("touch {}".format(fn))

        bmc_info = {
            "config_file": fn
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        assert "-c {}".format(fn) in bmc.get_commandline()
        os.system("rm -rf {}".format(fn))

    def test_set_invalid_config_file(self):
        fn = "/tmp/conf_test"
        os.system("rm -rf {}".format(fn))

        bmc_info = {
            "config_file": fn
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.set_config_file(fn)

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "Target config file doesn't exist:" in str(e)
        else:
            assert False

    def test_set_port_iol(self):
        bmc_info = {
            "ipmi_over_lan_port": 624
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()
        bmc.precheck()

        with open(bmc.get_config_file(), 'r') as fp:
            if "addr :: 624" in fp.read():
                assert True
            else:
                assert False

    def test_set_port_iol_negative(self):
        bmc_info = {
            "ipmi_over_lan_port": -1
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "Port for IOL(IPMI over LAN) is expected to be >= 0," \
                   in str(e)
        else:
            assert False

    def test_set_port_iol_not_int(self):
        bmc_info = {
            "ipmi_over_lan_port": "a!"
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("dell_r730")
        bmc.set_workspace(self.__class__.WORKSPACE)
        bmc.init()
        bmc.write_bmc_config()

        try:
            bmc.precheck()
        except ArgsNotCorrect, e:
            assert "Port for IOL(IPMI over LAN) is expected to be integer," \
                   in str(e)
        else:
            assert False


class socat_configuration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        socat.stop_socat()

    def test_default_socat(self):
        socat_obj = model.CSocat()

        socat_obj.init()
        socat_obj.precheck()
        cmd = socat_obj.get_commandline()

        assert "pty,link={}/pty0,waitslave".format(config.infrasim_etc) in cmd
        assert "unix-listen:{}/serial,fork".format(config.infrasim_etc) in cmd

    def test_change_sol_device(self):
        socat_obj = model.CSocat()

        socat_obj.set_sol_device("/tmp/sol_device")
        socat_obj.init()
        socat_obj.precheck()
        cmd = socat_obj.get_commandline()

        assert "pty,link=/tmp/sol_device,waitslave".format(config.infrasim_etc) in cmd

    def test_change_serial_socket(self):
        socat_obj = model.CSocat()

        socat_obj.set_socket_serial("/tmp/serial_socket")
        socat_obj.init()
        socat_obj.precheck()
        cmd = socat_obj.get_commandline()

        assert "unix-listen:/tmp/serial_socket,fork".format(config.infrasim_etc) in cmd


class monitor_configuration(unittest.TestCase):

    def test_default_monitor_in_qemu(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)
        try:
            del(node_info["monitor"])
        except KeyError:
            pass
        node = model.CNode(node_info)
        node.init()

        for element in node.get_task_list():
            if isinstance(element, model.CCompute):
                assert "-chardev socket,path=/home/infrasim/.infrasim/default/.monitor,"\
                       "id=monitorchardev,server,nowait "\
                       "-mon chardev=monitorchardev,mode=control" \
                    in element.get_commandline()

    def test_enable_monitor_in_qemu(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)

        node_info["monitor"] = {
            "enable": True
        }
        node = model.CNode(node_info)
        node.init()

        for element in node.get_task_list():
            if isinstance(element, model.CCompute):
                assert "-chardev socket,path=/home/infrasim/.infrasim/default/.monitor,"\
                       "id=monitorchardev,server,nowait "\
                        "-mon chardev=monitorchardev,mode=control" \
                    in element.get_commandline()

    def test_disable_monitor_in_qemu(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)

        node_info["monitor"] = {
            "enable": False
        }
        node = model.CNode(node_info)
        node.init()

        for element in node.get_task_list():
            if isinstance(element, model.CCompute):
                assert "-mon" not in element.get_commandline()

    def test_invalid_monitor_in_qemu(self):
        with open(config.infrasim_default_config, "r") as f_yml:
            node_info = yaml.load(f_yml)

        node_info["monitor"] = {
            "enable": "invalid"
        }
        node = model.CNode(node_info)
        try:
            node.init()
        except ArgsNotCorrect as e:
            assert "[Monitor] Invalid setting" in e.value
        else:
            assert False


class racadm_configuration(unittest.TestCase):

    def test_default_racadm(self):
        racadm_obj = model.CRacadm({})

        racadm_obj.init()
        racadm_obj.precheck()
        cmd = racadm_obj.get_commandline()

        assert "racadmsim default 0.0.0.0 10022 admin admin" in cmd

    def test_updated_racadm_info(self):
        racadm_info = {
            "interface": "lo",
            "port": 10023,
            "username": "fakeusername",
            "password": "fakepassword"
        }

        racadm_obj = model.CRacadm(racadm_info)

        racadm_obj.init()
        racadm_obj.precheck()
        cmd = racadm_obj.get_commandline()

        assert "racadmsim default 127.0.0.1 10023 fakeusername fakepassword" \
               in cmd

    def test_conflict_port(self):
        if not helper.check_if_port_in_use("0.0.0.0", 22):
            self.skipTest("Port 22 is not in use, skip port conflict test")

        racadm_info = {
            "port": 22
        }

        racadm_obj = model.CRacadm(racadm_info)

        racadm_obj.init()
        try:
            racadm_obj.precheck()
        except ArgsNotCorrect, e:
            assert ":22 is already in use" in str(e)

    def test_non_exist_interface(self):
        fake_interface = "fake0"

        racadm_info = {
            "interface": fake_interface
        }

        racadm_obj = model.CRacadm(racadm_info)

        racadm_obj.init()
        try:
            racadm_obj.precheck()
        except ArgsNotCorrect, e:
            assert "Specified racadm interface {} doesn\'t exist".\
                       format(fake_interface) in str(e)

class numa_configuration_1(unittest.TestCase):

    def setUp(self):
        self.numactl = helper.NumaCtl()
        self.numactl.__class__.HT_FACTOR = 2
        self.numactl._socket_list = [0, 1]
        self.numactl._core_list = [0, 1, 2, 3, 4, 8, 9, 10, 11, 12]
        self.numactl._core_map = {
            (0, 0): [0, 20], (1, 0): [1, 21],
            (0, 1): [2, 22], (1, 1): [3, 23],
            (0, 2): [4, 24], (1, 2): [5, 25],
            (0, 3): [6, 26], (1, 3): [7, 27],
            (0, 4): [8, 28], (1, 4): [9, 29],
            (0, 8): [10, 30], (1, 8): [11, 31],
            (0, 9): [12, 32], (1, 9): [13, 33],
            (0, 10): [14, 34], (1, 10): [15, 35],
            (0, 11): [16, 36], (1, 11): [17, 37],
            (0, 12): [18, 38], (1, 12): [19, 39]
        }
        self.numactl._core_map_avai = {
            (0, 0): [False, False], (1, 0): [False, False],
            (0, 1): [True, True], (1, 1): [True, True],
            (0, 2): [True, True], (1, 2): [True, True],
            (0, 3): [True, True], (1, 3): [True, True],
            (0, 4): [True, True], (1, 4): [True, True],
            (0, 8): [True, True], (1, 8): [True, True],
            (0, 9): [True, True], (1, 9): [True, True],
            (0, 10): [True, True], (1, 10): [True, True],
            (0, 11): [True, True], (1, 11): [True, True],
            (0, 12): [True, True], (1, 12): [True, True]
        }

    def tearDown(self):
        self.numactl = None

    def test_cpu_assign(self):
        assert self.numactl.get_cpu_list(4) == [2, 22, 4, 24]

    def test_cpu_assign_scattered_1(self):
        assert self.numactl.get_cpu_list(3) == [2, 22, 4]
        assert self.numactl.get_cpu_list(1) == [24]

    def test_cpu_assign_scattered_2(self):
        assert self.numactl.get_cpu_list(3) == [2, 22, 4]
        assert self.numactl.get_cpu_list(3) == [6, 26, 24]

    def test_cpu_assign_hyper_thread(self):
        assert self.numactl.get_cpu_list(8) == [2, 22, 4, 24, 6, 26, 8, 28]
        assert self.numactl.get_cpu_list(8) == [10, 30, 12, 32, 14, 34, 16, 36]
        assert self.numactl.get_cpu_list(8) == [3, 23, 5, 25, 7,27, 9, 29]
        assert self.numactl.get_cpu_list(8) == [11, 31, 13, 33, 15, 35, 17, 37]

    def test_no_enough_core_1(self):
        try:
            self.numactl.get_cpu_list(19)
        except Exception, e:
            assert str(e) == "All sockets don't have enough processor to bind."

    def test_no_enough_core_2(self):
        assert self.numactl.get_cpu_list(16) == [2, 22, 4, 24,
                                                6, 26, 8, 28,
                                                10, 30, 12, 32,
                                                14, 34, 16, 36]
        assert self.numactl.get_cpu_list(16) == [3, 23, 5, 25,
                                                7, 27, 9, 29,
                                                11, 31, 13, 33,
                                                15, 35, 17, 37]
        try:
            self.numactl.get_cpu_list(4)
        except Exception, e:
            assert str(e) == "All sockets don't have enough processor to bind."

class numa_configuration_2(unittest.TestCase):

    def setUp(self):
        self.numactl = helper.NumaCtl()
        self.numactl.__class__.HT_FACTOR = 1
        self.numactl._socket_list = [0, 1]
        self.numactl._core_list = [0, 1, 2, 3]
        self.numactl._core_map = {
            (0, 0): [0], (1, 0): [4],
            (0, 1): [1], (1, 1): [5],
            (0, 2): [2], (1, 2): [6],
            (0, 3): [3], (1, 3): [7]
        }
        self.numactl._core_map_avai = {
            (0, 0): [False], (1, 0): [False],
            (0, 1): [True], (1, 1): [True],
            (0, 2): [True], (1, 2): [True],
            (0, 3): [True], (1, 3): [True]
        }

    def tearDown(self):
        self.numactl = None

    def test_cpu_assign(self):
        assert self.numactl.get_cpu_list(3) == [1, 2, 3]

    def test_cpu_assign_scattered(self):
        assert self.numactl.get_cpu_list(2) == [1, 2]
        assert self.numactl.get_cpu_list(1) == [3]

    def test_no_enough_core_1(self):
        try:
            self.numactl.get_cpu_list(4)
        except Exception, e:
            assert str(e) == "All sockets don't have enough processor to bind."
