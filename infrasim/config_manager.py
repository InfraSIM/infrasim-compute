'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
import os
import yaml
from texttable import Texttable
from infrasim import config
from infrasim.yaml_loader import YAMLLoader
from infrasim import DirectoryNotFound, InfraSimError


class NodeMap(object):
    """
    This is a class manages infrasim mapping.
    """

    def __init__(self):
        self.__mapping_folder = config.infrasim_node_config_map
        self.__name_list = []

    def load(self):
        self.__name_list = []
        if not os.path.exists(self.__mapping_folder):
            raise DirectoryNotFound("InfraSIM MapManager failed to init due to {} folder not found.\n"
                                    "Please run this command to init:\n"
                                    "    infrasim init".
                                    format(self.__mapping_folder))
        node_list = os.listdir(self.__mapping_folder)
        for node in node_list:
            if node.endswith(".yml"):
                self.__name_list.append(node[:-4])

    def add(self, node_name, config_path):
        """
        Create a mapping for this node, by writing config
        to <node_name>.yml in mapping folder.
        """
        self.load()

        if node_name in self.__name_list:
            raise InfraSimError("Node {0}'s configuration already in InfraSIM mapping.\n"
                                "If you want to update the configuration, please run this command:\n"
                                "    infrasim node update {0} {1}".format(node_name, config_path))
        try:
            with open(config_path, 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
                if not isinstance(node_info, dict):
                    raise InfraSimError("Config {} is an invalid yaml file.".format(config_path))
                node_info["name"] = node_name
        except IOError:
            raise InfraSimError("Cannot find config {}".format(config_path))

        dst = os.path.join(self.__mapping_folder, "{}.yml".format(node_name))
        with open(dst, 'w') as fp:
            yaml.dump(node_info, fp, default_flow_style=False)
        os.chmod(dst, 0664)

        self.__name_list.append(node_name)
        print "Node {}'s configuration mapping added.".format(node_name)

    def delete(self, node_name):
        """
        Delete a mapping for this node, by deleting config
        of <node_name>.yml in mapping folder.
        """
        self.load()

        if node_name not in self.__name_list:
            raise InfraSimError("Node {0}'s configuration is not in InfraSIM mapping.".format(node_name))

        os.remove(os.path.join(self.__mapping_folder, "{}.yml".format(node_name)))

        self.__name_list.remove(node_name)
        print "Node {}'s configuration mapping removed".format(node_name)

    def update(self, node_name, config_path):
        """
        Update mapping configure for this node
        """
        self.load()

        if node_name not in self.__name_list:
            raise InfraSimError("Node {0}'s configuration is not in InfraSIM mapping.\n"
                                "Please add it to mapping folder with command:\n"
                                "    infrasim node add {0} {1}".format(node_name, config_path))
        try:
            with open(config_path, 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
                if not isinstance(node_info, dict):
                    raise InfraSimError("Config {} is an invalid yaml file.".format(config_path))
        except IOError:
            raise InfraSimError("Cannot find config {}".format(config_path))

        dst = os.path.join(self.__mapping_folder, "{}.yml".format(node_name))
        try:
            node_info["name"] = node_name
            with open(dst, 'w') as fp:
                yaml.dump(node_info, fp, default_flow_style=False)
            os.chmod(dst, 0664)
        except IOError:
            raise InfraSimError("Node {}'s configuration failed to be updated. Check file mode of {}.".format(node_name, dst))
        print "Node {}'s configuration mapping is updated".format(node_name)

    def list(self):
        """
        List all mapping in the map folder
        """
        self.load()

        table = Texttable()
        table.set_deco(Texttable.HEADER)
        rows = []
        rows.append(["name", "type"])
        for node_name in self.__name_list:
            node_type = ""
            with open(os.path.join(self.__mapping_folder, "{}.yml".format(node_name)), 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
                node_type = node_info["type"]
            rows.append([node_name, node_type])
        table.add_rows(rows)
        print table.draw()

    def get_mapping_folder(self):
        return self.__mapping_folder

    def get_name_list(self):
        return self.__name_list

    def get_node_info(self, node_name):
        src = os.path.join(self.__mapping_folder, "{}.yml".format(node_name))
        if not os.path.exists(src):
            raise InfraSimError("Node {0}'s configuration is not defined.\n"
                                "Please add config mapping with command:\n"
                                "    infrasim config add {0} [your_config_path]".format(node_name))
        with open(src, 'r') as fp:
            node_info = YAMLLoader(fp).get_data()
            return node_info
