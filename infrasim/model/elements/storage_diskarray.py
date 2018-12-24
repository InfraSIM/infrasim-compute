'''
*********************************************************
Copyright @ 2018 EMC Corporation All Rights Reserved
*********************************************************
'''
import json
import copy
import re
import struct
import os
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

    def __init__(self, ws):
        super(DiskArrayController, self).__init__()
        self._link = []
        self._expanders = []
        self._connections = []
        self._ports = []
        self._controllers = []
        self._sas_all_drv = os.path.join(ws, "sas_all_drives.json")

    def add_storage_chassis_backend(self, backend_info):
        # called in chassis.init for each sub node.
        backend = copy.deepcopy(backend_info)

        # set flag in orignal disk array object when it belongs to chassis.
        # so that it will not process again in node.start()
        for diskarray_controller in filter(lambda x: x["type"] == "disk_array", backend_info):
            diskarray_controller["sas_drives"] = self._sas_all_drv
        # add cloned node since it will be modified.
        self.add_storage_backend(backend)

    def __check_duplicated_diskarray(self, diskarray):
        # if any expander wwn existed in self._expanders, return true
        for item in diskarray["disk_array"]:
            encl = item.get("enclosure", {})
            for exp in encl.get("expanders", []):
                if len(filter(lambda x: x["wwn"] == exp["wwn"], self._expanders)) != 0:
                    return True
        return False

    def add_storage_backend(self, backend_info):
        # called in node.init
        diskarrays = filter(lambda x: x["type"] == "disk_array", backend_info)
        if len(diskarrays) == 0:
            return None
        if len(diskarrays) > 1:
            raise ArgsNotCorrect("[Disk Array] Only 1 Disk Array object Allowed")
        diskarray_controller = diskarrays[0]
        if diskarray_controller.get("sas_drives", None):
            # if it is handled by chassis already, clear and quit.
            self._expanders = []
            return

        if self.__check_duplicated_diskarray(diskarray_controller) is False:
            diskarray_controller["sas_drives"] = self._sas_all_drv
            self.__add_diskarray(diskarray_controller)

        controllers = filter(lambda x: x.get("connectors") or x.get("external_connectors"), backend_info)
        self._controllers.extend(controllers)
        for controller in controllers:
            self.__add_local_resource(controller)
        return diskarray_controller

    def __add_diskarray(self, diskarray):
        """
        step 1. collect all expanders
        step 2. collect all links.
        """
        # collect all resources
        for item in diskarray["disk_array"]:
            _raw_enclosure = item.get("enclosure")
            if _raw_enclosure:
                __drvs = _raw_enclosure.get("drives", [])
                exps = _raw_enclosure.pop("expanders", [])
                # set peer index
                peer_exp_index = len(self._expanders)
                if len(exps) == 2:
                    for expander in exps:
                        expander["peer_index"] = peer_exp_index + 1 - exps.index(expander)
                else:
                    for expander in exps:
                        index = expander.get("peer_index", exps.index(expander))
                        expander["peer_index"] = peer_exp_index + index

                for expander in exps:
                    # copy drive section and put it under expander.
                    expander["name"] = "{}_{}".format(item["name"], expander["name"])
                    expander["drives"] = __drvs
                    expander.get("ses", {})["dae_type"] = _raw_enclosure["type"]
                    self.__add_expander(expander)
            # collect all links between enclosures.
            self._connections.extend(item.get("connections", []))

    def __build_topology(self):
        """
        Collect all devices and build the connection net.
        """
        self.__add_connection_of_link()
        self.__add_connection_of_ses()
        self.__add_connection_of_drv()
        self.__allocate_scsi_id()

        """
        connection net is ready for traversal.
        1. Traversal connection net,
        2. Copy devices to controller.
        """
        for controller in self._controllers:
            self.__add_connection_of_hba(controller)
            self.__traversal_expanders(controller)
            self.__update_direct_scsi_id(controller)
            self.__get_ses(controller)
            self._ports.extend(controller["hba_ports"])
        self.__fill_empty_link()

    def get_topo(self):
        if len(self._expanders) == 0:
            # no expanders or chassis handled it.
            return None
        self.__build_topology()
        topo = {
            "expanders": self._expanders,
            "hba_ports": self._ports,
        }
        packer = TopoBin()
        content = packer.pack_topo(topo)
        return content

    def __add_expander(self, expander):

        phy_count = expander["phy_count"]
        ses = expander.get("ses")
        if ses:
            phy_count += 1
        expander["links"] = [None] * phy_count
        expander["phy_count"] = phy_count

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
            self.logger.warning("[Warning] Using default slot-phy-map for expander {0}".format(expander["wwn"]))
            result = range(_Const.DEFAULT_EXP_START_PHY, expander["phy_count"])
        expander["phy_map"] = result
        self._expanders.append(expander)

    def __update_link(self, exp, phy, num, atta_phy, atta_type, atta_wwn, atta_name=0, atta_slot_id=0):
        if atta_name == 0:
            atta_name = atta_wwn
        for temp in range(0, num):
            local_phy = phy + temp
            if exp["links"][local_phy] is not None:
                raise ArgsNotCorrect("Exp {} phy {} is not empty. {}".format(exp["name"], local_phy,
                                                                             exp["links"][local_phy]))
            exp["links"][local_phy] = {"phy": local_phy, "num": num - temp,
                                       "atta_wwn": atta_wwn, "atta_type": atta_type,
                                       "atta_dev_name": atta_name, "atta_phy": atta_phy + temp,
                                       "atta_scsi_id": 0, "atta_slot_id": atta_slot_id}

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

            self.__update_link(exp_a, peer_a["phy"], peer_a["number"], atta_type=_Const.EXP_DEVICE,
                               atta_wwn=exp_b["wwn"], atta_phy=peer_b["phy"])
            self.__update_link(exp_b, peer_b["phy"], peer_b["number"], atta_type=_Const.EXP_DEVICE,
                               atta_wwn=exp_a["wwn"], atta_phy=peer_a["phy"])

    def __add_connection_of_ses(self):
        for expander in self._expanders:
            ses = expander.get("ses")
            if ses:
                virtual_phy = expander["phy_count"] - 1
                ses["wwn"] = expander["wwn"] - 1
                self.__update_link(expander, virtual_phy, 1, atta_type=_Const.SES_DEVICE,
                                   atta_wwn=ses["wwn"], atta_name=ses["wwn"], atta_phy=0)

                ses["side"] = expander["side"]
                ses["port_wwn"] = ses["wwn"]

                def get_port_atta_wwn(name):
                    port = find(lambda p: p["id"] == name, expander["ports"])
                    if port is None:
                        return 0
                    link = expander["links"][port["phy"]]
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
                ses["serial"] = ses.get("serial") or ses.get("wwn")
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

    def __add_connection_of_drv(self):
        """
        add link to SAS drive
        """
        def format_value(src, value):
            """
            parse format of img name and plus initial value
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

                    self.__update_link(exp, phy, 1, atta_type=_Const.END_DEVICE, atta_phy=side,
                                       atta_wwn=drv["port_wwn"], atta_name=drv["wwn"], atta_slot_id=drv["slot_number"])

    def __traversal_expanders(self, controller):
        """
        traversal expander by link. Copy expander and drive.
        """
        controller.pop("external_connectors", None)
        ports = controller.get("connectors", [])
        hba = []

        def traversal(exps, wwn):
            exp = find(lambda exp: exp["wwn"] == wwn, self._expanders)
            if exp is None:
                self.logger.warning("[Warning] Empty port {0}".format(wwn))
                return
            if exp["visit"] is True:
                return
            exp["visit"] = True
            exps.append(self._expanders.index(exp))
            links = filter((lambda x: x is not None and x["atta_type"] == _Const.EXP_DEVICE), exp["links"])
            for link in links:
                traversal(exps, link["atta_wwn"])

        for port in ports:
            exps = []
            # first reset flag for all expanders in case not enter dead loop.
            for exp in self._expanders:
                exp["visit"] = False
            traversal(exps, port["atta_wwn"])
            # print(exps)
            hba_port = {
                "expanders": exps,
                "phy": port["phy"],
                "phy_number": port["phy_number"],
                "atta_type": _Const.EXP_DEVICE if len(exps) > 0 else _Const.NON_DEVICE,
                "atta_phy": port["atta_phy"],
                "atta_wwn": port["atta_wwn"],
                "wwn": port["wwn"],
                "name": controller["sas_address"]

            }
            # update physical port of ses object
            # physical_port of ses is not used anymore.

            hba.append(hba_port)

        controller["hba_ports"] = hba

    def __allocate_scsi_id(self):
        """
        allocate scsi_id for all devices
        """
        # update scsi_id of non-direct drv
        start_scsi_id = 32
        for exp in self._expanders:
            exp["start_scsi_id"] = start_scsi_id
            for link in filter((lambda x: x is not None), exp["links"]):
                link["atta_scsi_id"] = start_scsi_id + link["phy"]
                if link["atta_type"] == _Const.END_DEVICE:
                    drv = find(lambda d: d["port_wwn"] == link["atta_wwn"], exp["drives"])
                    drv["scsi-id"] = link["atta_scsi_id"]
                if link["atta_type"] == _Const.SES_DEVICE:
                    ses = exp["ses"]
                    ses["scsi-id"] = link["atta_scsi_id"]
            start_scsi_id = start_scsi_id + exp["phy_count"]

    def __fill_empty_link(self):
        for exp in self._expanders:
            links = exp["links"]
            for index in range(0, exp["phy_count"]):
                if links[index] is None:
                    links[index] = {
                        "phy": index,
                        "num": 0,
                        "atta_type": _Const.NON_DEVICE,
                        "atta_phy": 0,
                        "atta_slot_id": 0,
                        "atta_scsi_id": exp["start_scsi_id"] + index,
                        "atta_wwn": 0,
                        "atta_dev_name": 0
                    }

    def __update_direct_scsi_id(self, controller):
        # update scsi_id of direct attached drv
        hba_phys = range(0, controller.get("phys", 32))
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

    def __get_ses(self, controller):
        seses = []
        for port in controller.get("hba_ports", []):
            for index in port["expanders"]:
                exp = self._expanders[index]
                ses = exp.get("ses", None)
                if ses:
                    seses.append(ses)

        controller["seses"] = seses

    def __add_connection_of_hba(self, controller):
        """
        process connections to disk array.
        """

        def add_connector(port):
            # get the full name of expander
            # check empty port.
            if port.get("connected") is False:
                port["atta_wwn"] = 0
                port["atta_phy"] = 0
                port["phy_number"] = port.get("phy_number", 4)
                return
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
            self.__update_link(exp, local_phy, exp_port["number"], atta_type=_Const.HBA_DEVICE,
                               atta_phy=port["phy"], atta_wwn=port["wwn"])

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

    def set_topo_file(self, storage_backend_info, filename):
        for x in storage_backend_info:
            if x.get("connectors"):
                x["sas_topo"] = filename

    def export_drv_data(self):
        output = {}
        for controller in self._controllers:
            exp_ids = []
            drv_list = []
            for port in controller["hba_ports"]:
                for exp_id in port["expanders"]:
                    if exp_id in exp_ids:
                        continue
                    expander = self._expanders[exp_id]
                    drv_list.extend(expander["drives"])
                    exp_ids.append(exp_id)
            output[controller["sas_address"]] = {"drives": drv_list, "seses": controller["seses"]}

        with open(self._sas_all_drv, "w") as f:
            f.write(json.dumps(output, indent=2))

    def merge_drv_data(self, backend_storage_info):
        # find the file contains all drv in disk array.
        dae = filter(lambda x: x["type"] == "disk_array", backend_storage_info)
        if len(dae) == 0:
            return
        drv_list_file = dae[0]["sas_drives"]
        # load drv information
        with open(drv_list_file, "r") as f:
            element_list = json.load(f)
        # merge drive information to sas controller.
        for controller in backend_storage_info:
            sas_address = controller.get("sas_address", "0")
            sas_address = "{}".format(sas_address)
            if element_list.get(sas_address):
                drives = controller.get("drives", [])
                drives.extend(element_list[sas_address]["drives"])
                controller["drives"] = drives
                controller["seses"] = element_list[sas_address]["seses"]

    @staticmethod
    def export_drv_args(filename, drv_option_lists):
        with open(filename, "w") as f:
            f.write("count={}".format(len(drv_option_lists)))
            for opt in drv_option_lists:
                m = re.match("(?P<drv>-drive .*) (?P<dev>-device .*)", opt)
                f.write("\n{}\n{}\n".format(m.group("drv"), m.group("dev")))


class TopoBin():
    """
    typedef struct _Header
    {
       uint16_t tag;
       uint16_t nr_ports;
       uint16_t nr_total_exps;
       uint16_t offset;       // offset of expander structure, start from end of port structures.
    }Header;
    """
    HeaderFmt = "<HHHH"
    """
    typedef struct _Link
    {
       uint8_t phy;
       uint8_t num;
       uint8_t atta_type;
       uint8_t atta_phy;
       uint8_t atta_slot_id;
       uint8_t ___pad
       uint16_t atta_scsi_id;
       uint64_t atta_wwn;
       uint64_t atta_devname;
    }Link;
    """
    LinkFmt = "<BBBBBxHQQ"

    """
    typedef struct _exp
    {
       uint8_t phy_count;
       uint8_t side;
       uint16_t start_scsi_id;
       uint32_t peer_side;
       uint64_t wwn;
    } Exp;
    """
    ExpFmt = "<BBHlQ"
    """
    typedef struct _hba_port
    {
       uint8_t phy;
       uint8_t phy_count;
       uint8_t atta_type;
       uint8_t atta_phy;
       uint32_t expander_list_offset;
       uint64_t name
       uint64_t wwn;
       uint64_t atta_wwn;
    }HBA_port;
    """
    PortFmt = "<BBBBIQQQ"
    """
    typedef struct _hba_expander_list
    {
       uint32_t nr_expanders;
       uint32_t exp_offset[nr_expanders];
    }hba_expander_list;
    """

    def __init__(self):
        # port=32,exp=16,link=24
        assert(struct.calcsize(TopoBin.PortFmt) == 32)
        assert(struct.calcsize(TopoBin.ExpFmt) == 16)
        assert(struct.calcsize(TopoBin.LinkFmt) == 24)

    def __pack_port(self, port):
        return struct.pack(TopoBin.PortFmt,
                           port["phy"],
                           port["phy_number"],
                           port["atta_type"],
                           port["atta_phy"],
                           port["exp_list_offset"],
                           port["name"],
                           port["wwn"],
                           port["atta_wwn"])

    def __pack_exps_list(self, exps_list, max_number):
        result = []
        amount = len(exps_list)
        # print(exps_list)
        result.append(struct.pack("H", amount))
        for exp_id in exps_list:
            result.append(struct.pack("H", exp_id))
        pad = max_number - len(exps_list)
        result.append('\0\0' * pad)
        return "".join(result)

    def __update_peer_expander(self, all_expanders):
        '''
        translate peer index to position offset.
        '''
        offset = 0
        for exp in all_expanders:
            exp["offset"] = offset
            offset += struct.calcsize(TopoBin.ExpFmt) + exp["phy_count"] * struct.calcsize(TopoBin.LinkFmt)
        for exp in all_expanders:
            peer_index = exp["peer_index"]
            exp["peer_offset"] = all_expanders[peer_index]["offset"] - exp["offset"]

    def __pack_expander(self, exp):
        assert(exp["phy_count"] == len(exp["links"]))
        e = struct.pack(TopoBin.ExpFmt,
                        exp["phy_count"],
                        0,
                        exp["start_scsi_id"],
                        exp["peer_offset"],
                        exp["wwn"])
        result = [e]
        for link in exp["links"]:
            result.append(struct.pack(TopoBin.LinkFmt,
                                      link["phy"],
                                      link["num"],
                                      link["atta_type"],
                                      link["atta_phy"],
                                      link["atta_slot_id"],
                                      link["atta_scsi_id"],
                                      link["atta_wwn"],
                                      link["atta_dev_name"]))
        return "".join(result)

    def pack_topo(self, topo):
        """
        pack a dictionary to binary stream
        """
        result = []
        ports = []
        port_path = []
        exp_amount = len(topo["expanders"])
        offset = 0
        self.__update_peer_expander(topo["expanders"])
        for port in topo["hba_ports"]:
            # print("port {}".format(port["phy"]))
            # setup offset for expander list.
            port["exp_list_offset"] = offset
            # pack port.
            ports.append(self.__pack_port(port))
            # get list of connected expander
            exps_list = port["expanders"]
            # pack expanders under port for reference.
            port_path.append(self.__pack_exps_list(exps_list, exp_amount))
            offset += 1 + exp_amount  # pkus 1 for len field.

        # for safety, pad space of id list to 64bits
        pad = (offset + 3) / 4 * 4 - offset
        if pad:
            port_path.append("\0\0" * pad)
            offset += pad

        # generate header
        header = struct.pack(TopoBin.HeaderFmt, 0x1234, len(topo["hba_ports"]),
                             len(topo["expanders"]), offset)
        # pack all expanders.
        all_exps = []
        for exp in topo["expanders"]:
            all_exps.append(self.__pack_expander(exp))

        # form binary strucure.
        result.append(header)
        result.extend(ports)
        result.extend(port_path)
        result.extend(all_exps)
        return "".join(result)

    def unpack_topo(self, src):
        """
        unpack binary stream to dictionary.
        """
        def to_dict(values, *names):
            ret = {}
            for name in names:
                v = values[names.index(name)]
                ret[name] = v if v < 0x50000 else "{}={}".format(hex(v), v)
            return ret

        ret = {}
        header = to_dict(struct.unpack_from(TopoBin.HeaderFmt, src, 0), "tag", "nr_ports", "nr_total_exps", "offset")
        hba_ports = []
        expanders = []
        offset = struct.calcsize(TopoBin.HeaderFmt)
        for _ in range(0, header["nr_ports"]):
            port = to_dict(struct.unpack_from(TopoBin.PortFmt, src, offset),
                           "phy", "phy_count", "atta_type", "atta_phy", "expander_list_offset", "name", "wwn",
                           "atta_wwn")

            offset += struct.calcsize(TopoBin.PortFmt)
            hba_ports.append(port)

        exp_list_fmt = "<H" + "H" * header["nr_total_exps"]
        for i in range(0, header["nr_ports"]):
            explist = struct.unpack_from(exp_list_fmt, src, offset)
            offset += struct.calcsize(exp_list_fmt)
            hba_ports[i]["atta_expanders"] = {"count": explist[0], "ids": explist[1:explist[0] + 1]}

        offset = struct.calcsize(TopoBin.HeaderFmt) + header["nr_ports"] * \
            struct.calcsize(TopoBin.PortFmt) + header["offset"] * struct.calcsize('H')
        for _ in range(0, header["nr_total_exps"]):
            exp = to_dict(struct.unpack_from(TopoBin.ExpFmt, src, offset), "phy_count", "side", "start_scsi_id",
                          "peer_side", "wwn")
            expanders.append(exp)
            offset += struct.calcsize(TopoBin.ExpFmt)
            exp["link"] = []
            for _ in range(0, exp["phy_count"]):
                link = to_dict(struct.unpack_from(TopoBin.LinkFmt, src, offset),
                               "phy", "num", "atta_type", "atta_phy", "atta_slot_id", "atta_scsi_id",
                               "atta_wwn", "atta_dev_name")
                offset += struct.calcsize(TopoBin.LinkFmt)
                exp["link"].append(link)

        ret["header"] = header
        ret["ports"] = hba_ports
        ret["expander"] = expanders

        return ret
