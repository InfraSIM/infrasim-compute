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
from infrasim import config
from infrasim.config_manager import NodeMap
from infrasim.yaml_loader import YAMLLoader
from infrasim import InfraSimError
from test.fixtures import FakeConfig


class test_node_config_manager(unittest.TestCase):

    test_name = "test"
    test_config = os.path.join(config.infrasim_node_config_map, "test.yml")
    fake_name = "fake"
    fake_config = "fake.yml"
    tmp_config = "/tmp/abc.yml"
    init_config = config.infrasim_default_config

    nm = NodeMap()

    @classmethod
    def setUpClass(cls):
        try:
            os.remove(cls.test_config)
            os.remove(cls.fake_config)
        except:
            pass

    def tearDown(self):
        try:
            os.remove(self.test_config)
            os.remove(self.fake_config)
        except:
            pass

    def test_add_config(self):
        self.nm.add(self.test_name, self.init_config)
        with open(self.test_config, 'r') as fp:
            node_info = YAMLLoader(fp).get_data()
        assert node_info["name"] == "test"

    def test_add_duplicated_name(self):
        self.nm.add(self.test_name, self.init_config)
        try:
            self.nm.add(self.test_name, self.init_config)
        except InfraSimError, e:
            assert "configuration already in InfraSIM mapping" in e.value
        else:
            self.fail("Add duplicated name has no error.")

    def test_add_invalid_config(self):
        os.system("echo abc > {}".format(self.tmp_config))
        try:
            self.nm.add(self.test_name, self.tmp_config)
        except InfraSimError, e:
            os.system("rm {}".format(self.tmp_config))
            assert "is an invalid yaml file" in e.value
        else:
            os.system("rm {}".format(self.tmp_config))
            self.fail("Add invalid config has no error.")

    def test_add_non_exist_config(self):
        try:
            self.nm.add(self.test_name, self.fake_config)
        except InfraSimError, e:
            assert "Cannot find config" in e.value
        else:
            self.fail("Add non exist config has no error.")

    def test_delete_config(self):
        self.nm.add(self.test_name, self.init_config)
        self.assertTrue(os.path.exists(self.test_config))
        self.nm.delete(self.test_name)
        self.assertFalse(os.path.exists(self.test_config))

    def test_delete_non_exist_name(self):
        try:
            self.nm.delete(self.test_name)
        except InfraSimError, e:
            assert "configuration is not in InfraSIM mapping" in e.value
        else:
            self.fail("Delete non exist name has no error.")

    def test_update_config(self):
        self.nm.add(self.test_name, self.init_config)
        self.assertTrue(os.path.exists(self.test_config))
        new_info = FakeConfig().get_node_info()
        new_info["name"] = "didi"
        new_info["type"] = "dell_r730"
        with open(self.tmp_config, "w") as fp:
            yaml.dump(new_info, fp, default_flow_style=False)

        self.nm.update(self.test_name, self.tmp_config)
        with open(self.test_config) as fp:
            node_info = YAMLLoader(fp).get_data()
            assert node_info["type"] == "dell_r730"
            assert node_info["name"] == "test"
        os.remove(self.tmp_config)

    def test_update_non_exist_name(self):
        self.nm.add(self.test_name, self.init_config)
        self.assertTrue(os.path.exists(self.test_config))
        try:
            self.nm.update(self.fake_name, self.init_config)
        except InfraSimError, e:
            assert "configuration is not in InfraSIM mapping." in e.value
        else:
            self.fail("Update non exist node name with no error.")

    def test_update_non_exist_config(self):
        self.nm.add(self.test_name, self.init_config)
        self.assertTrue(os.path.exists(self.test_config))
        try:
            self.nm.update(self.test_name, self.fake_config)
        except InfraSimError, e:
            assert "Cannot find config" in e.value
        else:
            self.fail("Update non exist config file with no error.")

    def test_update_invalid_config(self):
        self.nm.add(self.test_name, self.init_config)
        self.assertTrue(os.path.exists(self.test_config))
        os.system("echo abc > {}".format(self.tmp_config))
        try:
            self.nm.update(self.test_name, self.tmp_config)
        except InfraSimError, e:
            os.system("rm {}".format(self.tmp_config))
            assert "is an invalid yaml file" in e.value
        else:
            os.system("rm {}".format(self.tmp_config))
            self.fail("Add invalid config has no error.")
