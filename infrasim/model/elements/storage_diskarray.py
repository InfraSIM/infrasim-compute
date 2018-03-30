'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import math
import sys
import json
from infrasim.model.core.element import CElement
from infrasim.dae import DAEProcessHelper
import copy
import re


class _Const:
    DEFAULT_EXP_START_PHY = 8
    NON_DEVICE = 0
    END_DEVICE = 1
    EXP_DEVICE = 2
    HBA_DEVICE = 4
    ACTIVE_DEVICE = 5
    SES_DEVICE = 13
    MAGIC_NUMBER = 0x23bc
    BIN_VER = 0x0


class DiskArrayController(CElement):
    """
    A pseodu controller handles the disk array object.
    """

    def __init__(self, diskarray):
        self._link = []
        self._expanders = {}
        # Rearrage item under diskarray to dictional and copy drives
        for item in diskarray["disk_array"]:
            _raw_enclosure = item.get("enclosure")
            if _raw_enclosure:
                __drvs = _raw_enclosure.get("drives", [])
                for expander in _raw_enclosure.get("expanders"):
                    # change to full name
                    expander["name"] = "{}_{}".format(item["name"], expander["name"])
                    # copy drive section and put it under expander.
                    expander["drives"] = __drvs
                    _ports = {}
                    for port in expander.pop("ports", []):
                        _ports[port["id"]] = port
                    expander["ports"] = _ports
                    self._expanders[expander["name"]] = expander
            # Adjust links between enclosures.
            _raw_links = item.get("connections", [])
            for _link in _raw_links:
                link = _link["link"]
                full_name_0 = "{}_{}".format(link[0]["disk_array"], link[0]["exp"])
                full_name_1 = "{}_{}".format(link[1]["disk_array"], link[1]["exp"])
                link[0]["peer"] = full_name_1
                link[1]["peer"] = full_name_0
                self._link.append({full_name_0:link[0], full_name_1:link[1]})
        # store the whole entity of backend storage
        self._backend_info = None

    def apply_device(self, backend_info):
        """
        assign expanders and drives to connected sas controller.
        """
        # print json.dumps(self._expanders, indent=4)
        # print json.dumps(self._link, indent=4)
        self._backend_info = backend_info
        for controller in backend_info:
            self.__process_local_expander(controller)
            self.__process_connectors(controller)
            self.__allocate_scsi_id(controller)
            print json.dumps(controller, indent=4)
        sys.exit(0)

    def __get_link(self, number, atta_wwn, atta_type, name=""):
        """
        :param number: amount of phys.
        :param atta_wwn: wwn of attached device
        :param atta_type: type of attached device
        :param name: name for debug.
        """
        return { "number":number, "atta_wwn": atta_wwn, "atta_type": atta_type, "atta_name": name }

    def __traversal_expanders(self, container, local_name):
        local_exp = container[local_name]
        for link in self._link:
            local = link.get(local_name)
            if local:
                peer_name = local["peer"]
                already_has = peer_name in container
                if already_has is False:
                    # if peer expander is no connected yet, get it from disk array pool.
                    peer_exp = copy.deepcopy(self._expanders.get(peer_name))
                    container[peer_name] = peer_exp
                    peer_exp["phys"] = {}
                    if peer_exp.get("ses"):
                        virtual_phy = peer_exp["phy_count"]
                        peer_exp["phys"][virtual_phy] = self.__get_link(1, peer_exp["wwn"] - 1, "ses", "ses")
                        peer_exp["phy_count"] = virtual_phy + 1
                peer = link.get(peer_name)
                peer_exp = container[peer_name]
                peer_exp["phys"] = peer_exp.get("phys", {})

                # mark expander's phy connects another expander
                phy = peer["phy"]
                link_a = self.__get_link(peer["number"], local_exp["wwn"], "exp", local_name)
                if peer_exp["phys"].get(phy) and peer_exp["phys"][phy] != link_a:
                    raise Exception("Phy {} of {} was occupied".format(phy, peer_name))
                peer_exp["phys"][phy] = link_a

                # mark expander's phy connects another expander
                phy = local["phy"]
                link_b = self.__get_link(local["number"], peer_exp["wwn"], "exp", peer_name)
                if local_exp["phys"].get(phy) and local_exp["phys"][phy] != link_b:
                    raise Exception("Phy {} of {} was occupied".format(phy, local_name))
                local_exp["phys"][phy] = link_b

                # if peer expander is newly connected, expand it now.
                if already_has is False:
                    self.__traversal_expanders(container, peer_name)

    def __allocate_scsi_id(self, controller):
        """
        allocate scsi_id for all devices under this controller
        """
        start_scsi_id = controller.get("phy_count", 8)
        for port in controller.get("connectors", []):
            for exp in port["exps"].values():
                exp["start_scsi_id"] = start_scsi_id
                slot_to_phy = exp.get("phy_map", range(0, exp["phy_count"]))

                drv_templates = exp.pop("drives")
                exp["drives"] = []
                side = exp["side"]
                for drv_template in drv_templates:
                    num_of_drv = drv_template.pop("repeat")
                    for index in range(num_of_drv):
                        phy = slot_to_phy[index + drv_template["slot_number"]]
                        drv = copy.deepcopy(drv_template)
                        drv["wwn"] = drv["wwn"] + 4 * index
                        drv["scsi_id"] = start_scsi_id + phy
                        drv["port_wwn"] = drv["wwn"] + side + 1
                        drv["target_wwn"] = drv["wwn"] + 3
                        drv["atta_wwn"] = exp["wwn"]
                        drv["serial"] = drv["serial"].format(phy)
                        drv["file"] = drv["file"].format(phy)
                        drv["atta_phy_id"] = phy
                        if exp["phys"].get(phy):
                            raise Exception("Phy {} in {} for drv was occupied".format(phy, exp["name"]))
                        exp["phys"][phy] = self.__get_link(1, drv["port_wwn"], "drv", "disk")
                        exp["drives"].append(drv)
                start_scsi_id = start_scsi_id + exp["phy_count"]

    def __process_connectors(self, controller):
        """
        process connections to disk array.
        """
        if controller.get("connectors"):
                # process connectors
                for port in controller["connectors"]:
                    # construct SAS tree under the port.
                    attached_expanders = {}
                    full_name = "{}_{}".format(port["atta_enclosure"], port["atta_exp"])
                    exp = self._expanders.get(full_name)
                    if exp:
                        exp = copy.deepcopy(exp)
                        attached_expanders[full_name] = exp
                        port_id = "{}".format(port["atta_port"])
                        # mark expander's phy connects HBA
                        exp_port = exp["ports"][port_id]
                        exp["phys"] = {exp_port["phy"] : self.__get_link(exp_port["number"], port["wwn"], "hba", "local_port")}
                        if exp.get("ses"):
                            virtual_phy = exp["phy_count"]
                            exp["phys"][virtual_phy] = self.__get_link(1, exp["wwn"] - 1, "ses", "ses")
                            exp["phy_count"] = virtual_phy + 1
                        self.__traversal_expanders(attached_expanders, full_name)

                        port["atta_type"] = "expander"
                        port["atta_phy"] = exp_port["phy"]
                        port["atta_wwn"] = exp["wwn"]
                    else:
                        raise Exception("Not found expander {}".format(full_name))
                    # process external_connectors
                    for exteral_port in controller.get("external_connectors", []):
                        full_name = "{}_{}".format(exteral_port["atta_enclosure"], exteral_port["atta_exp"])
                        port_id = "{}".format(exteral_port["atta_port"])
                        exp = attached_expanders.get(full_name)
                        if exp:
                            exp_port = exp["ports"][port_id]
                            a_link = self.__get_link(exp_port["number"], exteral_port["wwn"], "hba", "external_port")
                            if exp["phys"].get(exp_port["phy"]):
                                raise Exception("Port {} {} of External Connection is duplicated".format(full_name, port_id))
                            exp["phys"][exp_port["phy"]] = a_link

                    port["exps"] = attached_expanders

    def __process_local_expander(self, controller):
        """
        process direct expander( not belongs any diskarray enclosure)
        """
        pass

    @staticmethod
    def export_json_data(filename, args):
        if args is None:
            return
        drv_args = []
        drv_opt_list = args["drv_opt_list"]
        controller_info = args["controller_info"]
        for item in drv_opt_list:
            m = re.match("-drive (.*) -device (.*)", item)
            if m:
                drv_args.append({"drive": m.group(1), "device": m.group(2)})
        _o = {"drives": drv_args, "hba": controller_info['connectors']}

        controller_info.pop("connectors")
        controller_info.pop("drives")
        with open(filename, "w") as f:
            json.dump(_o, f, indent=2)

    def set_pci_topology_mgr(self, _):
        pass

    def init(self):
        """
        No more initialization needed.
        """
        pass

    def precheck(self):
        pass

    def handle_parms(self):
        pass

    def add_option(self, opt, _):
        pass

    def get_option(self):
        pass
