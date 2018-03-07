'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
import os
import yaml
from texttable import Texttable
from infrasim import config, chassis
from infrasim.yaml_loader import YAMLLoader
from infrasim import DirectoryNotFound, InfraSimError
from .log import LoggerType, infrasim_log

logger = infrasim_log.get_logger(LoggerType.config.value)


class BaseMap(object):
    """
    This is a class manages infrasim mapping.
    """

    def __init__(self, map_folder=""):
        self.__mapping_folder = map_folder
        self.__name_list = []
        self.__logger = None

    def get_logger(self, name):
        pass

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

    def add(self, item_name, config_path):
        logger_config = self.get_logger(item_name)
        """
        Create a mapping for this item, by writing config
        to <item_name>.yml in mapping folder.
        """
        logger_config.info("request rev: add item {0} with file {1}".format(item_name, config_path))
        try:
            self.load()
        except DirectoryNotFound, e:
            print e.value
            logger_config.exception(e.value)

        if item_name in self.__name_list:
            logger_config.exception("Item {0}'s configuration already in InfraSIM mapping.".
                                    format(item_name))
            raise InfraSimError("Item {0}'s configuration already in InfraSIM mapping.\n"
                                "If you want to update the configuration, please run this command:\n"
                                "    infrasim config update {0} {1}".format(item_name, config_path))
        try:
            with open(config_path, 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
                if not isinstance(node_info, dict):
                    logger_config.exception("Config {} is an invalid yaml file.".format(config_path))
                    raise InfraSimError("Config {} is an invalid yaml file.".format(config_path))
                node_info["name"] = item_name
                logger_config.info("Item {}'s yaml file: {}".format(item_name, node_info))
        except IOError:
            logger_config.exception("Cannot find config {}".format(config_path))
            raise InfraSimError("Cannot find config {}".format(config_path))

        dst = os.path.join(self.__mapping_folder, "{}.yml".format(item_name))
        with open(dst, 'w') as fp:
            yaml.dump(node_info, fp, default_flow_style=False)
        os.chmod(dst, 0664)

        self.__name_list.append(item_name)
        print "Item {}'s configuration mapping added.".format(item_name)
        logger_config.info("request res: Item {}'s configuration mapping added.".format(item_name))

    def delete(self, item_name):
        """
        Delete a mapping for this item, by deleting config
        of <item_name>.yml in mapping folder.
        """
        logger_config = self.get_logger(item_name)
        logger_config.info("request rev: delete item {}".format(item_name))
        try:
            self.load()
        except DirectoryNotFound, e:
            print e.value
            logger_config.exception(e.value)

        if item_name not in self.__name_list:
            logger_config.exception("Item {}'s configuration is not in InfraSIM mapping.".format(item_name))
            raise InfraSimError("Item {0}'s configuration is not in InfraSIM mapping.".format(item_name))

        os.remove(os.path.join(self.__mapping_folder, "{}.yml".format(item_name)))

        self.__name_list.remove(item_name)
        print "Item {}'s configuration mapping removed".format(item_name)
        logger_config.info("request res: Item {}'s configuration mapping removed.".format(item_name))

    def update(self, item_name, config_path):
        """
        Update mapping configure for this item
        """
        logger_config = self.get_logger(item_name)
        logger_config.info("request rev: update item {0} with file {1}".format(item_name, config_path))
        try:
            self.load()
        except DirectoryNotFound, e:
            print e.value
            logger_config.exception(e.value)

        if item_name not in self.__name_list:
            logger_config.exception("Item {0}'s configuration is not in InfraSIM mapping.".
                                    format(item_name))
            raise InfraSimError("Item {0}'s configuration is not in InfraSIM mapping.\n"
                                "Please add it to mapping folder with command:\n"
                                "    infrasim item add {0} {1}".format(item_name, config_path))
        try:
            with open(config_path, 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
                if not isinstance(node_info, dict):
                    logger_config.exception("Config {} is an invalid yaml file.".format(config_path))
                    raise InfraSimError("Config {} is an invalid yaml file.".format(config_path))
                logger_config.info("Item {}'s yaml file: {}".format(item_name, node_info))
        except IOError:
            logger_config.exception("Cannot find config {}".format(config_path))
            raise InfraSimError("Cannot find config {}".format(config_path))

        dst = os.path.join(self.__mapping_folder, "{}.yml".format(item_name))
        try:
            node_info["name"] = item_name
            with open(dst, 'w') as fp:
                yaml.dump(node_info, fp, default_flow_style=False)
            os.chmod(dst, 0664)
        except IOError:
            logger_config.exception("Item {}'s configuration failed to be updated.".format(item_name))
            raise InfraSimError("Item {}'s configuration failed to be updated. Check file mode of {}.".format(item_name, dst))
        print "Item {}'s configuration mapping is updated".format(item_name)
        logger_config.info("request res: Item {}'s configuration mapping is updated".format(item_name))

    def list(self):
        """
        List all mapping in the map folder
        """

        logger.info("request rev: list")
        try:
            self.load()
        except DirectoryNotFound, e:
            print e.value
            logger.exception(e.value)

        table = Texttable()
        table.set_deco(Texttable.HEADER)
        rows = []
        rows.append(["name", "type"])
        for node_name in self.__name_list:
            node_type = ""
            with open(os.path.join(self.__mapping_folder, "{}.yml".format(node_name)), 'r') as fp:
                node_info = YAMLLoader(fp).get_data()
                node_type = node_info['type']
            rows.append([node_name, node_type])
        table.add_rows(rows)
        print table.draw()
        logger.info("request res: list OK")

    def get_mapping_folder(self):
        return self.__mapping_folder

    def get_name_list(self):
        self.load()
        return self.__name_list

    def get_item_info(self, item_name):
        logger_config = self.get_logger(item_name)
        src = os.path.join(self.__mapping_folder, "{}.yml".format(item_name))
        if not os.path.exists(src):
            logger_config.exception("Item {0}'s configuration is not defined.".format(item_name))
            raise InfraSimError("Item {0}'s configuration is not defined.\n"
                                "Please add config mapping with command:\n"
                                "    infrasim config add {0} [your_config_path]".format(item_name))
        with open(src, 'r') as fp:
            node_info = YAMLLoader(fp).get_data()
            return node_info


class NodeMap(BaseMap):

    def __init__(self):
        map_folder = config.infrasim_node_config_map
        super(NodeMap, self).__init__(map_folder)

    def get_logger(self, name):
        return infrasim_log.get_logger(LoggerType.config.value, name)


class ChassisMap(BaseMap):

    def __init__(self, nm):
        super(ChassisMap, self).__init__(config.infrasim_chassis_config_map)
        self.__nm = nm
        self.__chassis_name = None

    def get_logger(self, name):
        return infrasim_log.get_chassis_logger(name)

    def __load(self, config_path):
        item_name = self.__chassis_name
        logger_config = self.get_logger(item_name)

        try:
            with open(config_path, 'r') as fp:
                chassis_info = YAMLLoader(fp).get_data()
        except IOError:
            logger_config.exception("Cannot find config {}".format(config_path))
            raise InfraSimError("Cannot find config {}".format(config_path))

        if not isinstance(chassis_info, dict):
            logger_config.exception("Config {} is an invalid yaml file.".format(config_path))
            raise InfraSimError("Config {} is an invalid yaml file.".format(config_path))

        nodes = chassis_info.get("nodes")
        if not nodes:
            raise InfraSimError("Config {} has no [nodes].".format(chassis_info))
        for node in nodes:
            if not node.get('name'):
                node['name'] = "{}_node_{}".format(item_name, nodes.index(node))
        return chassis_info

    def __split_sub_nodes(self, config_path):
        item_name = self.__chassis_name
        logger_config = self.get_logger(item_name)
        sub_nodes = []
        chassis_info = self.__load(config_path)

        for node in chassis_info["nodes"]:
            node_name = node['name']
            filename = os.path.join("/tmp/", node_name + ".yml")
            with open(filename, 'w') as fo:
                yaml.dump(node, fo, default_flow_style=False)
            os.chmod(filename, 0664)
            sub_nodes.append({"node_name":node_name, "file":filename})
            logger_config.info("Item {}'s yaml file: {}".format(node_name, filename))
        return sub_nodes

    def __get_node_names(self, config_path):
        item_name = self.__chassis_name
        logger_config = self.get_logger(item_name)
        sub_nodes = []
        chassis_info = self.__load(config_path)
        nodes = chassis_info.get("nodes")
        for node in nodes:
            sub_nodes.append(node['name'])
            logger_config.info("Sub nodes names {}".format(sub_nodes))
        return sub_nodes

    def add(self, item_name, config_path):
        self.__chassis_name = item_name
        installed_node = []
        logger_config = self.get_logger(item_name)
        sub_nodes = self.__split_sub_nodes(config_path)
        node_name = ""
        try:
            for node in sub_nodes:
                node_name = node["node_name"]
                self.__nm.add(node_name, node["file"]);
                installed_node.append(node_name)
        except InfraSimError as e:
            for node in installed_node:
                self.__nm.delete(node)
            raise InfraSimError("Node {0} in {1} is already existed.".format(node_name, item_name))
        super(ChassisMap, self).add(item_name, config_path)
        print "Chassis {} is added with nodes:{}.".format(item_name, installed_node)
        logger_config.info("Chassis {} is added with nodes:{}.".format(item_name, installed_node))

    def delete(self, item_name):
        self.__chassis_name = item_name
        config_path = os.path.join(self.get_mapping_folder(), "{}.yml".format(item_name))
        node_names = self.__get_node_names(config_path)
        for node in node_names:
            self.__nm.delete(node);
        super(ChassisMap, self).delete(item_name)

    def update(self, item_name, config_path):
        self.__chassis_name = item_name
        logger_config = self.get_logger(item_name)
        sub_nodes = self.__split_sub_nodes(config_path)
        node_name = ""
        installed_node = []
        for node in sub_nodes:
            node_name = node["node_name"]
            self.__nm.update(node_name, node["file"]);
            installed_node.append(node_name)
        super(ChassisMap, self).update(item_name, config_path)
        print "Chassis {} is updated with nodes:{}.".format(item_name, installed_node)
        logger_config.info("Chassis {} is updated with nodes:{}.".format(item_name, installed_node))

