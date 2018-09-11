import copy
import os
import re
import shutil
import subprocess
import yaml
import codecs
import json

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
from infrasim.model.elements.storage_diskarray import DiskArrayController


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
        ns_list = re.findall(r'(\w+)(\s+\(id)?', ns_string)
        nodes = self.__chassis.get("nodes", [])
        for node in nodes:
            ns_name = node["namespace"]
            if ns_name not in [ns[0] for ns in ns_list]:
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
        self.__process_disk_array()

        self._init_sub_node(*args)

        self.__process_oem_data()
        # save data to exchange file.
        self.__dataset.save(self.__file_name)

        self.__daemon.init(self.workspace.get_workspace())
        self.__daemon.start()

        self.__render_chassis_info()
        self.__update_node_cfg()
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
            ws = os.path.join(config.infrasim_home, node["name"])
            ws_data = os.path.join(ws, "data")

            def get_file(src, default_name):
                if src is None:
                    dst = os.path.join(ws_data, default_name)
                else:
                    dst = os.path.join(ws_data, os.path.basename(src))
                return dst
            bios_file = get_file(node["compute"].get("smbios"), "{}_smbios.bin".format(node["type"]))
            bios = SMBios(bios_file)
            bios.ModifyType3ChassisInformation(data["sn"])
            # bios.ModifyType2BaseboardInformation("")
            bios.save(bios_file)

            emu_file = get_file(node.get("bmc", {}).get("emu_file"), "{}.emu".format(node["type"]))
            emu = FruFile(emu_file)
            emu.ChangeChassisInfo(data["pn"], data["sn"])
            emu.Save(emu_file)

            node["compute"]["smbios"] = bios_file
            bmc = node.get("bmc", {})
            node["bmc"] = bmc
            bmc["emu_file"] = emu_file

    def __update_node_cfg(self):
        """
        refresh yml file of node
        """
        for node in self.__chassis.get("nodes"):
            ws = os.path.join(config.infrasim_home, node["name"])
            ws_etc = os.path.join(ws, "etc")
            yml_file = os.path.join(ws_etc, "infrasim.yml")
            with open(yml_file, 'w') as fp:
                yaml.dump(node, fp, default_flow_style=False)

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
        # len_status_error =  sizeof(SCSIStatusError)
        # typedef struct SCSIStatusError
        # {
        #     ErrorType error_type; //BUSY CHECK_CONDITION ABORT ACA
        #     uint32_t count;
        #     SCSISense sense;
        #     uint64_t l_lbas[1024][2];
        # }SCSIStatusError;

        len_status_error = 1 + 4 + 3 + 1024 * 8 * 2 + 8
        data = {
            "serial": drv["serial"],
            "log_page": '\0' * 2048,
            "status_error": '\0' * len_status_error,
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
        # len_status_error = sizeof(StatusError)
        # typedef struct StatusError {
        #     StatusField status_field;
        #     uint32_t count;
        #     Opcode opcode;
        #     uint32_t nsid;
        #     uint64_t lbas[1024][2];
        # } StatusError;
        len_status_error = 4 + 4 + 1 + 4 + 1024 * 8 * 2 + 3
        data = {
            "serial": drv["serial"].encode(),
            "feature": '\0' * len_feature,
            "status_error": '\0' * len_status_error,
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

        # set sharemeory id for sub node.
        for node in self.__chassis.get("nodes"):
            node["compute"]["communicate"] = {"shm_key": "share_mem_{}".format(self.__chassis_name)}
            node["bmc"] = node.get("bmc", {})
            node["bmc"]["shm_key"] = "share_mem_{}".format(self.__chassis_name)

    def __process_oem_data(self):
        '''
        process oem data json
        VPD, Health data of NVME.
        '''
        def oem_string_2_binary(src):
            return filter(lambda x: x != ' ', src).decode('hex')

        # load oem_data.json of chassis
        oem_data_file = os.path.join(self.workspace.get_workspace_data(), "oem_data.json")
        if os.path.exists(oem_data_file):
            # copy oem data to each sub nodes.
            for node in self.__chassis.get("nodes"):
                dst = os.path.join(config.infrasim_home, node["name"], "data")
                if os.path.exists(dst):
                    shutil.copy(oem_data_file, dst)
            # load and parse oem data
            with codecs.open(oem_data_file, 'r', 'utf-8') as f:
                oem_data = json.load(f)
            # fill share memory according to slot_x
            nvme_data = oem_data.get("nvme")
            if nvme_data:
                # only process nvme
                for slot in filter(lambda x: x.get("type") == "nvme", self.__chassis.get("slots", [])):
                    for x in range(slot.get("repeat", 1)):
                        slot_id = "slot_{}".format(slot["chassis_slot"] + x)
                        data = nvme_data.get(slot_id)
                        if data is None:
                            # skip it, if there is no slot_x in oem data file
                            continue
                        self.__dataset[slot_id]["vpd"] = oem_string_2_binary(data["vpd"])
                        self.__dataset[slot_id]["health"] = oem_string_2_binary(data["health_data"])

    def __process_disk_array(self):
        ws = self.workspace.get_workspace_data()
        diskarray = DiskArrayController(ws)
        # set sharemeory id for sub node.
        for node in self.__chassis.get("nodes", []):
            storage = node["compute"].get("storage_backend")
            diskarray.add_storage_chassis_backend(storage)

        topo = diskarray.get_topo()
        if topo:
            for node in self.__chassis.get("nodes", []):
                storage = node["compute"].get("storage_backend")
                diskarray.set_topo_file(storage, "sas_topo")
            self.__dataset.append("sas_topo", topo)
            diskarray.export_drv_data()
