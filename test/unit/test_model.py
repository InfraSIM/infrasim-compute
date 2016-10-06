#!/usr/bin/env python
'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import unittest
import yaml
from infrasim import ArgsNotCorrect
from infrasim import model
from infrasim import socat
from infrasim import config


class qemu_functions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.system("touch test.yml")

    @classmethod
    def tearDownClass(cls):
        os.system("rm -rf test.yml")

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

    def test_set_ahci_storage_controller(self):
        try:
            backend_storage_info = [{
                "controller": {
                    "type": "ahci",
                    "max_drive_per_controller": 6,
                    "drives": [{"size": 8}]
                }
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device ahci" in storage.get_option()
        except:
            assert False

    def test_set_scsi_storage_controller(self):
        try:
            backend_storage_info = [{
                "controller": {
                    "type": "scsi",
                    "max_drive_per_controller": 8,
                    "drives": [{"size": 8}]
                }
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "-device scsi" in storage.get_option()
        except:
            assert False

    def test_set_ahci_storage_controller_2x(self):
        try:
            backend_storage_info = [{
                "controller": {
                    "type": "ahci",
                    "max_drive_per_controller": 2,
                    "drives": [{"size": 8}, {"size": 8}, {"size": 8}]
                }
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "sata1.2" in storage.get_option()
        except:
            assert False

    def test_set_ahci_drive_model(self):
        try:
            backend_storage_info = [{
                "controller": {
                    "type": "ahci",
                    "max_drive_per_controller": 6,
                    "drives": [{"size": 8, "model": "SATADOM"}]
                }
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
                "controller": {
                    "type": "ahci",
                    "max_drive_per_controller": 6,
                    "drives": [
                        {"size": 8, "model": "SATADOM", "serial": "HUSMM442"}
                    ]
                }
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
                "controller": {
                    "type": "megasas-gen2",
                    "max_drive_per_controller": 6,
                    "drives": [
                        {"size": 8, "serial": "HUSMM442",
                         "model": "SATADOM", "vendor": "Hitachi"}],
                }
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
                "controller": {
                    "type": "megasas-gen2",
                    "max_drive_per_controller": 6,
                    "drives": [{
                        "size": 8, "model": "SATADOM",
                        "serial": "HUSMM442", "vendor": "Hitachi",
                        "rotation": 1
                    }]
                }
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
                "controller": {
                    "type": "megasas-gen2",
                    "max_drive_per_controller": 6,
                    "drives": [{
                            "size": 8, "model": "SATADOM",
                            "serial": "HUSMM442", "vendor": "Hitachi",
                            "rotation": 1, "product": "Quanta"}]
                }
            }]
            storage = model.CBackendStorage(backend_storage_info)
            storage.init()
            storage.precheck()
            storage.handle_parms()
            assert "product" in storage.get_option()
        except:
            assert False

    def test_set_smbios(self):
        with open(config.infrasim_initial_config, "r") as f_yml:
            compute_info = yaml.load(f_yml)["compute"]
        compute_info["smbios"] = "/tmp/test.smbios"

        compute = model.CCompute(compute_info)
        compute.init()
        assert compute.get_smbios() == "/tmp/test.smbios"

    def test_set_smbios_without_workspace(self):
        with open(config.infrasim_initial_config, "r") as f_yml:
            compute_info = yaml.load(f_yml)["compute"]

        compute = model.CCompute(compute_info)
        compute.set_type("s2600kp")
        compute.init()
        assert compute.get_smbios() == \
            os.environ['HOME'] + "/.infrasim/data/s2600kp/s2600kp_smbios.bin"

    def test_set_smbios_with_type_and_workspace(self):
        with open(config.infrasim_initial_config, "r") as f_yml:
            compute_info = yaml.load(f_yml)["compute"]
        workspace = os.path.join(os.environ["HOME"], ".infrasim", ".test")

        compute = model.CCompute(compute_info)
        compute.set_type("s2600kp")
        compute.set_workspace(workspace)
        compute.init()
        assert compute.get_smbios() == os.path.join(workspace,
                                                    "data",
                                                    "s2600kp_smbios.bin")


class bmc_configuration(unittest.TestCase):

    WORKSPACE = "{}/.infrasim/.test".format(os.environ["HOME"])

    @classmethod
    def setUpClass(cls):
        with open(config.infrasim_initial_config, 'r') as f_yml:
            conf = yaml.load(f_yml)
        conf["name"] = ".test"
        with open("test.yml", 'w') as f_yml:
            yaml.dump(conf, f_yml, default_flow_style=False)

        cls.node = model.CNode(conf)
        cls.node.set_node_name(".test")
        cls.node.init_workspace()
        socat.start_socat("test.yml")

    @classmethod
    def tearDownClass(cls):
        socat.stop_socat("test.yml")
        with open("test.yml", 'r') as f_yml:
            conf = yaml.load(f_yml)
        cls.node = model.CNode(conf)
        cls.node.init()
        cls.node.terminate_workspace()
        os.system("rm test.yml")

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
        bmc.set_type("quanta_d51")
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

    def test_set_startnow_true(self):
        bmc_info = {
            "startnow": True
        }

        bmc = model.CBMC(bmc_info)
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
        bmc.set_workspace(self.__class__.WORKSPACE)
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        bmc.set_type("quanta_d51")
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
        assert "udp-listen:9003,reuseaddr" in cmd
