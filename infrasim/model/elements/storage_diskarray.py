'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import json
import copy
import re
from infrasim.model.core.element import CElement
from infrasim import ArgsNotCorrect


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


def find(f, container):
    """
    helper function of searching element
    """
    for item in container:
        if f(item):
            return item
    return None


class DiskArrayController(CElement):
    """
    A pseodu controller handles the disk array object.
    """

    def __init__(self, diskarray):
        """
        step 1. collect all expanders
        step 2. collect all links.
        """
        super(DiskArrayController, self).__init__()
        self._link = []
        self._expanders = []
        self._connections = []
        # collect all resources
        for item in diskarray["disk_array"]:
            _raw_enclosure = item.get("enclosure")
            if _raw_enclosure:
                __drvs = _raw_enclosure.get("drives", [])
                for expander in _raw_enclosure.pop("expanders", []):
                    # copy drive section and put it under expander.
                    expander["name"] = "{}_{}".format(item["name"], expander["name"])
                    expander["drives"] = __drvs
                    ses = expander.get("ses")
                    if ses:
                        ses["dae_type"] = _raw_enclosure["type"]

                    self.__add_expander(expander)
            # collect all links between enclosures.
            self._connections.extend(item.get("connections", []))
        # store the whole entity of backend storage
        self._backend_info = None

    def apply_device(self, backend_info):
        """
        Collect all devices and build the connection net.
        """
        for controller in backend_info:
            self.__add_local_resource(controller)
            self.__add_connection_of_hba(controller)

        self.__add_connection_of_link()
        self.__add_connection_of_ses()
        self.__add_connection_of_drv()

        self.__reformat_links()
        """
        connection net is ready for traversal.
        1. Traversal connection net,
        2. Copy devices to controller.
        3. Allocate scsi_id.
        """
        for controller in backend_info:
            if controller.get("connectors"):
                self.__traversal_expanders(controller)
                self.__update_scsi_id(controller)
                self.__format(controller)

    def __add_expander(self, expander):
        expander["links"] = {}
        expander["visit"] = False
        phy_map = expander.pop("phy_map", None)
        if phy_map:
            result = []
            matchs = re.findall(r"(\d+)(?:-(\d+))?", phy_map)
            for m in matchs:
                start = int(m[0])
                stop = int(m[0] if m[1] == "" else m[1])
                if start <= stop:
                    stop += 1
                    result.extend(range(start, stop))
                else:
                    stop -= 1
                    result.extend(range(start, stop, -1))
        else:
            result = range(_Const.DEFAULT_EXP_START_PHY, expander["phy_count"])
        expander["phy_map"] = result
        self._expanders.append(expander)

    def __append_link(self, exp, phy, link):
        if exp["links"].get(phy):
            raise ArgsNotCorrect("Exp {} phy {} conflict".format(exp["wwn"], phy))
        exp["links"][phy] = link

    def __add_connection_of_link(self):
        """
        process link between disk array.
        """
        def __find_expander_by_link(peer):
            name = ""
            if peer.get("disk_array"):
                name = "{}_".format(peer["disk_array"])
            name = "{}{}".format(name, peer["exp"])
            exp = find(lambda exp: exp["name"] == name, self._expanders)
            return exp

        for link in self._connections:
            peer_a = link["link"][0]
            peer_b = link["link"][1]

            exp_a = __find_expander_by_link(peer_a)
            exp_b = __find_expander_by_link(peer_b)

            self.__append_link(exp_a, peer_a["phy"], self.__get_link(peer_a["phy"], peer_a["number"],
                                                                     exp_b["wwn"], peer_b["phy"],
                                                                     _Const.EXP_DEVICE))
            self.__append_link(exp_b, peer_b["phy"], self.__get_link(peer_b["phy"], peer_b["number"],
                                                                     exp_a["wwn"], peer_a["phy"],
                                                                     _Const.EXP_DEVICE))

    def __add_connection_of_ses(self):
        for expander in self._expanders:
            ses = expander.get("ses")
            if ses:
                virtual_phy = expander["phy_count"]
                ses["wwn"] = expander["wwn"] - 1
                self.__append_link(expander, virtual_phy,
                                   self.__get_link(virtual_phy, 1, ses["wwn"], 0, _Const.SES_DEVICE))
                expander["phy_count"] = virtual_phy + 1
                ses["side"] = expander["side"]
                ses["port_wwn"] = ses["wwn"]

                def get_port_atta_wwn(name):
                    port = find(lambda p: p["id"] == name, expander["ports"])
                    if port is None:
                        return 0
                    link = expander["links"].get(port["phy"], None)
                    if link:
                        return link["atta_wwn"]
                    else:
                        self.logger.warning(
                            "[Warning] No connection at port id={1} of expander {0}".format(expander["wwn"], name))
                        return 0
                ses["pp_atta_sas_addr"] = get_port_atta_wwn("pp") or get_port_atta_wwn(0)
                ses["ep_atta_sas_addr"] = get_port_atta_wwn("ep") or get_port_atta_wwn(1)
                ses["channel"] = 0
                ses["lun"] = 0
                ses["serial"] = ses["wwn"]
                ses["ses_buffer_file"] = ses.pop("buffer_data", "")
                ses["physical_port"] = 0

    def __add_local_resource(self, controller):
        """
        process direct expander( not belongs any diskarray enclosure)
        """
        for expander in controller.pop("expanders", []):
            ses = expander.get("ses")
            if ses:
                ses["dae_type"] = ses.get("dae_type", 28)
            self.__add_expander(expander)

    def __get_link(self, local_phy, number, atta_wwn, atta_phy, atta_type, atta_name=None):
        """
        :param number: amount of phys.
        :param atta_wwn: wwn of attached device
        :param atta_type: type of attached device
        :param name: name for debug.
        """

        if atta_name is None:
            atta_name = atta_wwn
        return {"phy": local_phy, "num": number,
                "atta_wwn": atta_wwn, "atta_type": atta_type,
                "atta_dev_name": atta_name, "atta_phy": atta_phy}

    def __add_connection_of_drv(self):
        """
        add link to SAS drive
        """
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

        for exp in self._expanders:
            drv_templates = exp.pop("drives", [])
            exp["drives"] = []
            side = exp.get("side", 0)
            slot_to_phy = exp["phy_map"]
            # generate drv node according template.
            for drv_template in drv_templates:
                num_of_drv = drv_template.get("repeat", 1)
                for index in range(num_of_drv):
                    drv = copy.deepcopy(drv_template)
                    drv["slot_number"] = drv["slot_number"] + index
                    if drv["slot_number"] < 0 or len(slot_to_phy) < drv["slot_number"]:
                        raise ArgsNotCorrect("slot_number exceeds phy_map in expander {}".format(exp["wwn"]))
                    phy = slot_to_phy[drv["slot_number"]]
                    drv["wwn"] = drv["wwn"] + 4 * index
                    drv["port_wwn"] = drv["wwn"] + side + 1
                    drv["target_wwn"] = drv["wwn"] + 3
                    drv["atta_wwn"] = exp["wwn"]
                    if drv.get("serial"):
                        drv["serial"] = format_value(drv["serial"], index)
                    if drv["file"]:
                        drv["file"] = format_value(drv["file"], index)
                    drv["atta_phy_id"] = phy
                    exp["drives"].append(drv)
                    self.__append_link(exp, phy, self.__get_link(phy, 1, drv["port_wwn"], side,
                                                                 _Const.END_DEVICE, drv["wwn"]))

    def __reformat_links(self):
        # reformat "links" field of expander.
        # change to list from dict.
        for exp in self._expanders:
            exp["links"] = sorted(exp.pop("links").values(), key=lambda l: l["phy"])

    def __traversal_expanders(self, controller):
        """
        traversal expander by link. Copy expander and drive.
        """
        controller.pop("external_connectors", None)
        ports = controller.pop("connectors", [])
        # first reset flag for all expanders in case not enter dead loop.
        for exp in self._expanders:
            exp["visit"] = False
        hba = []

        def traversal(exps, wwn):
            exp = find(lambda exp: exp["wwn"] == wwn, self._expanders)
            if exp is None:
                raise ArgsNotCorrect("Wrong connection to exp {}".format(wwn))
            if exp["visit"] is True:
                return
            exp["visit"] = True
            exps.append(copy.deepcopy(exp))
            wwns = [link["atta_wwn"] for link in exp["links"] if link["atta_type"] == _Const.EXP_DEVICE]
            for wwn in wwns:
                traversal(exps, wwn)

        for port in ports:
            exps = []
            traversal(exps, port["atta_wwn"])
            hba_port = {
                "expanders": exps,
                "phy": port["phy"],
                "phy_number": port["phy_number"],
                "atta_type": _Const.EXP_DEVICE,
                "atta_phy": port["atta_phy"],
                "atta_wwn": port["atta_wwn"],
                "wwn": port["wwn"]

            }
            # update physical port of ses object
            physical_port_index = ports.index(port)
            for exp in exps:
                ses = exp.get("ses", {})
                ses["physical_port"] = physical_port_index
            hba.append(hba_port)

        controller["hba_ports"] = hba

    def __update_scsi_id(self, controller):
        """
        allocate scsi_id for all devices under this controller
        """
        hba_phys = set(range(controller.get("phy_count", 8)))
        # update scsi_id of non-direct drv
        start_scsi_id = 0  # controller.get("phy_count", 8)
        for port in controller.get("hba_ports", []):
            phys = set(range(port["phy"], port["phy"] + port["phy_number"]))
            if not phys <= hba_phys:
                raise ArgsNotCorrect("HBA {} phy {} conflict".format(port["wwn"], phys))
            hba_phys -= phys
            for exp in port["expanders"]:
                exp["start_scsi_id"] = start_scsi_id
                for link in exp["links"]:
                    link["atta_scsi_id"] = start_scsi_id + link["phy"]
                    if link["atta_type"] == _Const.END_DEVICE:
                        drv = find(lambda d: d["port_wwn"] == link["atta_wwn"], exp["drives"])
                        drv["scsi-id"] = link["atta_scsi_id"]
                    if link["atta_type"] == _Const.SES_DEVICE:
                        ses = exp["ses"]
                        ses["scsi-id"] = link["atta_scsi_id"]
                start_scsi_id = start_scsi_id + exp["phy_count"]

        # update scsi_id of direct attached drv
        direct_drvs = controller.get("drives", [])
        for drv in direct_drvs:
            if drv.get("atta_phy"):
                phy = drv["atta_phy"]
                if phy not in hba_phys:
                    raise ArgsNotCorrect("wrong atta_phy:{} of drv {}".format(phy, hex(drv["wwn"])))
                hba_phys.remove(phy)
            else:
                if len(hba_phys) == 0:
                    raise ArgsNotCorrect("no more free phy of hba for drv {}".format(hex(drv["wwn"])))
                phy = hba_phys.pop()

            drv["atta_phy"] = phy
            drv["scsi-id"] = phy
            drv["port_wwn"] = drv["wwn"] + 1
            drv["target_wwn"] = drv["wwn"] + 2

    def __format(self, controller):
        """
        copy drives and seses to controller.
        """
        drv = controller.pop("drives", [])
        seses = []
        for port in controller.get("hba_ports", []):
            for exp in port["expanders"]:
                exp.pop("ports", None)
                exp.pop("visit", None)
                exp.pop("side", None)
                exp.pop("phy_map", None)
                exp["exp_wwn"] = exp.pop("wwn")
                drv.extend(exp.pop("drives", []))
                ses = exp.pop("ses", None)
                if ses:
                    seses.append(ses)

        controller["drives"] = drv
        controller["seses"] = seses

    def __add_connection_of_hba(self, controller):
        """
        process connections to disk array.
        """

        def add_connector(port):
            # get the full name of expander
            full_name = ""
            if port.get("atta_enclosure"):
                full_name = "{}_".format(port["atta_enclosure"])
            full_name = "{}{}".format(full_name, port["atta_exp"])
            # find the expander
            exp = find(lambda exp: exp["name"] == full_name, self._expanders)
            if exp is None:
                raise ArgsNotCorrect("No expander named {}".format(full_name))
            # find the specified port
            exp_port = find(lambda p: p["id"] == port["atta_port"], exp["ports"])
            if exp_port is None:
                raise ArgsNotCorrect("No expander port {1} in {0} ".format(full_name, port["atta_port"]))
            # get the phy id of found port
            local_phy = exp_port["phy"]
            self.__append_link(exp, local_phy, self.__get_link(local_phy, exp_port["number"],
                                                               port["wwn"], port["phy"],
                                                               _Const.HBA_DEVICE))
            port["atta_wwn"] = exp["wwn"]
            port["atta_phy"] = local_phy
            port["phy_number"] = exp_port["number"]

        if controller.get("connectors"):
                # process connectors
            for port in controller["connectors"]:
                add_connector(port)
            # process external_connectors
            for port in controller.get("external_connectors", []):
                add_connector(port)

    @staticmethod
    def export_json_data(filename, drv_option_lists, controller):
        drv_args = []
        for item in drv_option_lists:
            m = re.match("-drive (.*) -device (.*)", item)
            if m:
                drv_args.append({"drive": m.group(1), "device": m.group(2)})
        _o = {"drives": drv_args, "hba": controller.pop('hba_ports', [])}

        with open(filename, "w") as f:
            json.dump(_o, f, indent=2)
        controller.pop("drives")

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
