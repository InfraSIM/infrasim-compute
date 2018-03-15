from infrasim.model import CNode, CChassisDaemon
from infrasim.helper import NumaCtl
from infrasim.chassis.dataset import DataSet
from infrasim.workspace import ChassisWorkspace
import subprocess

import shutil
import traceback
import pprint
import yaml
import sys
import copy
from infrasim.log import infrasim_log
import re


class CChassis(object):
    def __init__(self, chassis_name, chassis_info):
        self.__chassis = chassis_info
        self.__chassis_model = None
        self.__node_list = {}
        self.__chassis_name = chassis_name
        self.__numactl_obj = NumaCtl()
        self.__dataset = DataSet(chassis_name)
        self.__file_name = "/tmp/{}_chassis_data.bin".format(chassis_name)
        self.__daemon = CChassisDaemon(chassis_name, self.__file_name)
        self.logger = infrasim_log.get_chassis_logger(chassis_name)
        self.workspace = None

    options = {
        "precheck": CNode.precheck,
        "init": CNode.init,
        "start": CNode.start,
        "stop": CNode.stop,
        "destroy": CNode.terminate_workspace
    }

    def process_by_node_names(self, action, *args):
        node_names = list(args) or self.__node_list.keys()
        all_node_names = set(self.__node_list.keys())
        selected_node_names = all_node_names.intersection(set(node_names))
        for name in selected_node_names:
            self.options[action](self.__node_list[name])


    def __check_namespace(self):
        ns_string = subprocess.check_output(["ip","netns","list"])
        ns_list = re.findall(r'(\w+) \(id',ns_string)
        nodes = self.__chassis.get("nodes", [])
        for node in nodes:
            ns_name = node["namespace"]
            if ns_name not in ns_list:
                raise Exception("Namespace {0} doesn't exist".format(ns_name))
    
    
    def precheck(self, *args):
        # check total resources
        self.__check_namespace()
        self.process_by_node_names("precheck", *args)

    def init(self, *args):
        self.workspace = ChassisWorkspace(self.__chassis)
        nodes = self.__chassis.get("nodes", [])
        bk_nodes = copy.deepcopy(nodes)
        self.__process_chassis_device()
        for node in nodes:
            node_obj = CNode(node)
            node_name = node.get("name")
            if node_name is None:
                node_name = "{}_node_{}".format(self.__chassis_name, nodes.index(node))
                node["name"] = node_name
            node_obj.set_node_name(node["name"])
            self.__node_list[node["name"]] = node_obj
        self.__chassis["nodes"] = bk_nodes
        self.workspace.init()
        self.process_by_node_names("init", *args)


    def start(self, *args):
        self.__dataset.load()
        self.__dataset.fill(self.__file_name)
        self.__daemon.init(self.workspace.get_workspace())
        self.__daemon.start()
        self.__create_namespace()
        self.process_by_node_names("start", *args)

    def stop(self, *args):
        self.__daemon.init(self.workspace.get_workspace())
        self.process_by_node_names("stop", *args)
        # TODO: save data if need.
        self.__daemon.terminate()

    def destroy(self, *args):
        self.init(*args)
        self.stop(*args)
        self.process_by_node_names("destroy", *args)
        if ChassisWorkspace.check_workspace_exists(self.__chassis_name):
            shutil.rmtree(self.workspace.get_workspace())
        self.logger.info("[Chassis] Chassis {} runtime workspcace is destroyed".
                           format(self.__chassis_name))
        print "Chassis {} runtime workspace is destroyed.".format(self.__chassis_name)

    def status(self):
        for node_obj in self.__node_list:
            node_obj.status()

    def __create_namespace(self):
        """
        Create name space for sub nodes.
        """
        self.logger.info("Prepare namespace for each nodes.")
        pass

    def __process_chassis_data(self, data):
        if data is None:
            return

    def __process_chassis_slots(self, slots):
        for node in self.__chassis.get("nodes"):
            node["compute"]["storage_backend"] = node["compute"].get("storage_backend", [])
        nvme_dev = []
        sas_dev = []
        for item in slots:
            if item.get("type") == "nvme":
                # process nvme device.
                nvme_dev.append(copy.deepcopy(item))
            else:
                # process SAS drive
                drv = copy.deepcopy(item)
                sas_dev.append(drv)
                drv["slot_number"] = drv.pop("chassis_slot")
        # create a disk array object.
        diskarray = {"disk_array":
                         [{"enclosure":
                          {"drives":sas_dev,
                           "expanders":[
                               {"name":"lcc-0",
                                "phy_count":36,
                                "ports":[
                                    {"id": "pp",
                                     "number":4,
                                     "phy":0}],
                                "ses": {"buffer_data": "/home/infrasim/workspace/bins/buffer.bin"},
                                "side":0,
                                "wwn":5764611469514216639},
                               {"name":"lcc-1",
                                "phy_count":36,
                                "ports":[
                                    {"id": "pp",
                                     "number":4,
                                     "phy":0}],
                                "ses": {"buffer_data": "/home/infrasim/workspace/bins/buffer.bin"},
                                "side":1,
                                "wwn":5764611469514216655}
                               ],
                           "type": 28
                           },
                          "name": "chassis"
                          }],
                         "type":"disk_array"
                         }
        for node in self.__chassis.get("nodes"):
            for controller in node["compute"]["storage_backend"]:
                if controller.get("slot_range") is not None:
                    node["compute"]["storage_backend"].append(copy.deepcopy(diskarray))
                    # insert it to controller with one connection.
                    controller["connectors"]=[{"atta_enclosure":"chassis",
                                               "atta_exp":"lcc-{}".format(self.__chassis.get("nodes").index(node)),
                                               "atta_port":"pp",
                                               "phy":0,
                                               "wwn":controller["sas_address"]}]
      
                    break
            node["compute"]["storage_backend"].extend(nvme_dev)
                    

    def __process_chassis_device(self):
        '''
        assign IDs of shared devices
        merge shared device to node.
        '''
        self.logger.info("Assign ShareMemoryId for shared device.")
        chassis = self.__chassis.get('chassis', {})
        if chassis is None:
            return
        self.__process_chassis_data(chassis.get("data"))
        self.__process_chassis_slots(chassis.get("slots", []))

        with open("/home/infrasim/workspace/out.yml", 'w') as fp:
            yaml.dump(self.__chassis, fp, default_flow_style=False, indent=4)
        # sys.exit("test __process_chassis_device done.")
