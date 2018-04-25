import copy
import os
import re
import shutil
import subprocess

from infrasim import config
from infrasim import InfraSimError
from infrasim.chassis.dataset import DataSet
from infrasim.chassis.emu_data import FruFile
from infrasim.chassis.smbios import SMBios
from infrasim.helper import NumaCtl
from infrasim.log import infrasim_log
from infrasim.model import CNode
from infrasim.model.tasks.chassis_daemon import CChassisDaemon
from infrasim.workspace import ChassisWorkspace


class CChassis(object):

    def __init__(self, chassis_name, chassis_info):
        self.__chassis = chassis_info
        self.__chassis_model = None
        self.__node_list = {}
        self.__chassis_name = chassis_name
        self.__numactl_obj = NumaCtl()
        self.__dataset = DataSet()
        self.__file_name = None
        self.__daemon = None
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
        ns_string = subprocess.check_output(["ip", "netns", "list"])
        ns_list = re.findall(r'(\w+) \(id', ns_string)
        nodes = self.__chassis.get("nodes", [])
        for node in nodes:
            ns_name = node["namespace"]
            if ns_name not in ns_list:
                raise Exception("Namespace {0} doesn't exist".format(ns_name))

    def precheck(self, *args):
        # check total resources
        self.__check_namespace()
        self.process_by_node_names("precheck", *args)

    def init(self):
        self.workspace = ChassisWorkspace(self.__chassis)
        nodes = self.__chassis.get("nodes")
        if nodes is None:
            raise InfraSimError("There is no nodes under chassis")
        for node in nodes:
            node_name = node.get("name", "{}_node_{}".format(self.__chassis_name, nodes.index(node)))
            node["name"] = node_name
            node["type"] = self.__chassis["type"]
        self.workspace.init()
        self.__file_name = os.path.join(self.workspace.get_workspace_data(), "shm_data.bin")
        self.__daemon = CChassisDaemon(self.__chassis_name, self.__file_name)

    def _init_sub_node(self, *args):
        nodes = self.__chassis.get("nodes")
        for node in nodes:
            node_obj = CNode(node)
            node_obj.set_node_name(node["name"])
            self.__node_list[node["name"]] = node_obj
        self.process_by_node_names("init", *args)

    def start(self, *args):
        self.__process_chassis_device()
        self.__daemon.init(self.workspace.get_workspace())
        self.__daemon.start()
        self._init_sub_node(*args)

        self.__render_chassis_info()
        self.process_by_node_names("start", *args)

    def stop(self, *args):
        self._init_sub_node(*args)
        self.process_by_node_names("stop", *args)
        # TODO: export data if need.
        self.__daemon.init(self.workspace.get_workspace())
        self.__daemon.terminate()

    def destroy(self, *args):
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

    def __render_chassis_info(self):
        """
        update smbios and emulation data.
        """
        data = self.__chassis["data"]
        for node in self.__chassis.get("nodes"):
            bios_file = os.path.join(config.infrasim_home, node["name"],
                                     "data", "{}_smbios.bin".format(node["type"]))
            bios = SMBios(bios_file)
            bios.ModifyType3ChassisInformation(data["sn"])
            # bios.ModifyType2BaseboardInformation("")
            bios.save(bios_file)
            emu_file = os.path.join(config.infrasim_home, node["name"],
                                    "data", "{}.emu".format(node["type"]))
            emu = FruFile(emu_file)
            emu.ChangeChassisInfo(data["pn"], data["sn"])
            emu.Save(emu_file)

    def __process_chassis_data(self, data):
        if data is None:
            return

        buf = {}
        for key in data.keys():
            if "pn" in key or "sn" in key:
                buf[key] = "{}".format(data[key]).encode()

        buf["led"] = ' ' * data.get("led", 20)

        self.__dataset.append("chassis", buf)

    def __translate_user_data(self, src):
        """
        process custom data.
        """
        ret = {}
        for k, v in src.items():
            if isinstance(v, int):
                value = '\0' * v  # treat int value as buffer size.
            if isinstance(v, str):
                value = v.encode()  # treat string as user data
            if isinstance(v, dict):
                value = self.__translate_user_data(v)
            ret[k] = value
        return ret

    def __process_sas_drv_data(self, drv):
        # universal data for SAS drv
        data = {
            "serial": drv["serial"],
            "log_page": '\0' * 2048,
            "mode_page": '\0' * 2048
        }
        if drv.get("user_data"):
            # add custom data if it has
            data["user_data"] = self.__translate_user_data(drv["user_data"])
        self.__dataset.append("slot_{}".format(drv["slot_number"]), data)

    def __process_nvme_data(self, drv):
        # universal data for NVMe drv
        num_queues = drv.get("queues", 64)
        elpe = drv.get("elpe", 3)
        # len_feature = sizeof(NvmeFeatureVal) + sizeof(uint32_t) * n->num_queues;
        # NvmeFeatureVal = 10 * uint32_t + 4 * uint64_t
        len_feature = 4 * 10 + 8 * 4 + 4 * num_queues
        # len_error_log_page = sizeof(NvmeErrorLog) * (n->elpe + 1) +
        # sizeof(num_errors) + sizeof(error_count) + sizeof(elp_index) + pad_byte
        len_error_log_page = 64 * (elpe + 1) + 4
        data = {
            "serial": drv["serial"].encode(),
            "feature": '\0' * len_feature,
            "elpes": '\0' * len_error_log_page
        }
        if drv.get("user_data"):
            # add custom data if it has
            data["user_data"] = self.__translate_user_data(drv["user_data"])
        self.__dataset.append("slot_{}".format(drv["chassis_slot"]), data)

    def __process_chassis_slots(self, slots):
        nvme_dev = []
        sas_dev = []

        def format_value(src, value):
            """
            parse format and plus initial value
            """
            m = re.match(r"^(?P<pre>.+){(?P<initial>\d+)}(?P<post>.*)$", src)
            if m:
                src = "{0}{1}{2}".format(m.group('pre'), value + int(m.group('initial')), m.group('post'))
            else:
                src = src.format(value)
            return src
        for item in slots:
            if item.get("type") == "nvme":
                # process nvme device.
                for x in range(item.get("repeat", 1)):
                    drv = copy.deepcopy(item)
                    drv["chassis_slot"] = drv["chassis_slot"] + x
                    drv["file"] = format_value(drv["file"], x)
                    drv["serial"] = format_value(drv["serial"], x)
                    drv["id"] = format_value(drv["id"], x)
                    if drv.get("bus"):
                        drv["bus"] = format_value(drv["bus"], x)
                    nvme_dev.append(drv)
                    self.__process_nvme_data(drv)
            else:
                # process SAS drive
                for x in range(item.get("repeat", 1)):
                    drv = copy.deepcopy(item)
                    sas_dev.append(drv)
                    drv["slot_number"] = drv.pop("chassis_slot") + x
                    drv["wwn"] = drv["wwn"] + x * 4
                    drv["serial"] = format_value(drv["serial"], x)
                    drv["file"] = format_value(drv["file"], x)
                    self.__process_sas_drv_data(drv)

        for node in self.__chassis.get("nodes"):
            # insert nvme drive
            node["compute"]["storage_backend"].extend(nvme_dev)
            # insert sas drive.
            for controller in node["compute"]["storage_backend"]:
                if controller.get("slot_range"):
                    controller["drives"] = controller.get("drives", [])
                    slot_range = [int(x) for x in controller["slot_range"].split('-')]
                    for drv in sas_dev:
                        if drv["slot_number"] >= slot_range[0] and drv["slot_number"] < slot_range[1]:
                            controller["drives"].append(drv)
                            drv["port_wwn"] = drv["wwn"] + 1 + self.__chassis["nodes"].index(node)
                    break

    def __process_chassis_device(self):
        '''
        assign IDs of shared devices
        merge shared device to node.
        '''
        self.__process_chassis_data(self.__chassis.get("data"))
        self.__process_chassis_slots(self.__chassis.get("slots", []))
        # save data to exchange file.
        self.__dataset.save(self.__file_name)
        # set sharemeory id for sub node.
        for node in self.__chassis.get("nodes"):
            node["compute"]["communicate"] = {"shm_key": "share_mem_{}".format(self.__chassis_name)}
