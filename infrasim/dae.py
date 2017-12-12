import json
import re

"""
  Note:
  DAEProcessHelper is the entry to this module.
  All other classes, including Const, Link, Enclosure, Drv, Expander and
  DAEController,  are used to store internal data for building topology.
  Ref: https://github.com/InfraSIM/infrasim-compute/wiki/Disk-Array-Topology-Design
"""


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

    @staticmethod
    def check_range_conflict(phy0, number0, phy1, number1):
        if not (phy0 >= (phy1 + number1) or (phy0 + number0) <= phy1):
            return True
        return False


class _SNGenerator(object):
    INDEX = 0
    SN_PREFIX = "Z4C03{0:03X}"

    @classmethod
    def reset(cls, prefix):
        if prefix is not None:
            cls.SN_PREFIX = prefix.replace("{}", "{0:03X}")
        else:
            cls.SN_PREFIX = "Z4C03{0:03X}"
        cls.INDEX = 0

    @classmethod
    def getSN(cls):
        sn = cls.SN_PREFIX.format(cls.INDEX)
        cls.INDEX += 1
        return sn


class _Link(object):
    def __init__(self, phy, num, atta_type, atta_phy, atta_wwn, atta_dev_name,
                 atta_slot_id=0):
        self.phy = phy
        self.num = num
        self.atta_type = atta_type
        self.atta_phy = atta_phy
        self.atta_wwn = atta_wwn
        self.atta_dev_name = atta_dev_name
        self.atta_slot = atta_slot_id

    def __str__(self):
        return "{:2},{},{},{:2},{},{}".format(
            self.phy,
            self.num,
            self.atta_type,
            self.atta_phy,
            self.atta_wwn,
            self.atta_dev_name)

    def get_obj_in_dict(self):
        """
            Get link information in dict format
            return: dictionary containing link information
        """
        return {"phy": self.phy,
                "num": self.num,
                "atta_type": self.atta_type,
                "atta_phy": self.atta_phy,
                "atta_wwn": self.atta_wwn,
                "atta_dev_name": self.atta_dev_name,
                "atta_slot_id": self.atta_slot}

    def update_link(self, atta_type, atta_phy, atta_wwn, atta_dev_name):
        """
            Overwrite link's information with given attributes
        """
        self.atta_type = atta_type
        self.atta_phy = atta_phy
        self.atta_wwn = atta_wwn
        self.atta_dev_name = atta_dev_name


class _Drv(object):
    def __init__(self, cfg, index):
        self.__link = []
        self.__cfg = cfg.copy()
        self.__cfg['slot_number'] = index
        self.__cfg['file'] = cfg['file'].format(index)
        # each drive occupis 4 wwn. base wwn, 2 port wwns, target wwn.
        self.__cfg['wwn'] = cfg['wwn'] + 4 * index
        self.__cfg['serial'] = _SNGenerator.getSN()

    def connect(self, link):
        """
            append link to the drive's link list
        """
        self.__link.append(link)

    def get_wwn(self, port_index):
        """
            get port wwn in terms of port index.
        """
        return self.__cfg['wwn'] + port_index + 1

    def get_dev_name(self):
        """
            get drive's device name
        """
        # get base wwn.
        return self.__cfg['wwn']

    def print_link(self):
        for l in self.__link:
            print(l)

    def __str__(self, *args, **kwargs):
        return object.__str__(self.__cfg)

    def get_port_cfg(self, port_index):
        """
            return a map copy for specific port index. fill device info attached
            to the drive's port
        """
        _cfg = self.__cfg.copy()
        _cfg['port_wwn'] = self.get_wwn(port_index)
        for link in self.__link:
            if link.phy == port_index:
                _cfg['atta_wwn'] = link.atta_wwn
                _cfg['atta_phy_id'] = link.atta_phy
                break
        return _cfg


class _Expander(object):
    def __init__(self, cfg, dae_type):
        self.__cfg = cfg
        self.__link = []
        self.name = cfg['name']
        self.phy_count = cfg['phy_count']
        # attributes of ses
        self.__ses_attributes = None
        self.__visit_status = False
        self.__port_link = []
        self.__init_ports(cfg['ports'])
        self.__init_ses(dae_type)

    def __init_ports(self, ports):
        """
            init the expander's port links as defined in expander's "ports"
            list.
            ports: the "ports" section in the expander's configuration
        """
        for port in ports:
            link = _Link(port['phy'], port['number'], _Const.NON_DEVICE,
                         0, 0, 0)
            self.__port_link.append({"id": port["id"], "link": link})

    def connect(self, link):
        """
            add link to the expander's link list. raise error if duplicates.
        """
        for item in self.__link:
            if _Const.check_range_conflict(link.phy, link.num, item.phy,
                                           item.num):
                raise Exception(
                    "Duplicate phy usage for link in expander {}, "
                    "phy {}, num {}".format(self.name, link.phy, link.num))

        self.__link.append(link)

    def __init_ses(self, dae_type):
        """
        init attributes of ses if specified
        """
        if self.__cfg.get('ses'):
            # attributes of ses
            self.__ses_attributes = {}
            self.__ses_attributes['channel'] = 0
            self.__ses_attributes['dae_type'] = dae_type
            self.__ses_attributes['ep_atta_sas_addr'] = 0  # reset it later
            self.__ses_attributes['lun'] = 0
            self.__ses_attributes['physical_port'] = 0  # reset it later
            self.__ses_attributes['pp_atta_sas_addr'] = 0  # reset it later
            self.__ses_attributes['scsi-id'] = 0  # reset it later
            self.__ses_attributes['side'] = self.__cfg['side']
            # ses_wwn = exp_wwn - 1
            self.__ses_attributes['wwn'] = self.__cfg['wwn'] - 1
            # ses serial = ses wwn
            self.__ses_attributes['serial'] = self.__cfg['wwn'] - 1
            self.__ses_attributes['ses_buffer_file'] = self.__cfg['ses']['buffer_data']
            self.__ses_link = _Link(self.phy_count, 1, _Const.SES_DEVICE, 0,
                                    self.__ses_attributes['wwn'],
                                    self.__ses_attributes['wwn'])
            self.phy_count += 1
            self.connect(self.__ses_link)

    def get_port_link(self):
        """
            get expander's port links
        """
        return self.__port_link

    def get_wwn(self, _=None):
        """
            get expander's wwn
        """
        return self.__cfg['wwn']

    def get_dev_name(self):
        """
            get expander's device name
        """
        return self.__cfg['wwn']

    def get_link_number(self):
        """
            get number of links to the expander
        """
        return len(self.__link)

    def print_link(self):
        for l in self.__link:
            print(l)

    def set_visited(self, status):
        """
            set visited flag for the expander, which is used during traversal.
            this flag is set to avoid duplicate enumaration if the expander can
            be reached from different paths.
            status: value of visited flag. True or False.
        """
        s = self.__visit_status
        self.__visit_status = status
        return s

    def traversal(self, seses_dict, port, encl, scsi_id_index):
        """
            iterate through all expanders under given port
            seses_dict: descriptions of ses object found during the iteration.
            port: port of HBA.
            encl: enclosure objects consist of expanders.
            scsi_id_index: start scsi id for each traversal

            return:dictionary of traversal result including expanders and links
        """
        start_scsi_id = scsi_id_index[0]
        links = []
        for l in self.__link:
            links.append(l.get_obj_in_dict())

        links.sort(key=lambda l: l['phy'])
        ret = [{"exp_wwn": self.__cfg['wwn'],
                "phy_count": self.phy_count,
                "start_scsi_id": start_scsi_id,
                "links": links}]

        self.set_visited(True)
        scsi_id_index[0] = start_scsi_id + self.phy_count
        if self.__ses_attributes:
            # set ses attributes
            self.__ses_attributes['scsi-id'] = start_scsi_id + \
                self.phy_count - 1
            self.__ses_attributes['physical_port'] = port
        _ses = self.get_dict_of_ses()
        if _ses:
            seses_dict.append(_ses)
        for l in self.__link:
            if l.atta_type == _Const.EXP_DEVICE:
                _exp = encl.find_expander(l.atta_wwn)
                if _exp.set_visited(True) is False:
                    ret = ret + \
                        _exp.traversal(seses_dict, port, encl, scsi_id_index)
        return ret

    def find_link_obj_by_port_id(self, port_id):
        """
            Find expander's port link by port id
            port_id: port's index specified in expander's ports configuration

            return: dictionary of port link
        """
        for port in self.__port_link:
            if port['id'] == port_id:
                return port['link']
        raise Exception("can't find port in internal connection.")

    def get_dict_of_ses(self):
        """
           Fill in ses object's attribute dictionary from expander
           return: ses attributes dictionary
        """
        if self.__ses_attributes:
            for port in self.__port_link:
                if ((port['id'] == 0 or port['id'] == "pp") and
                        port['link'].atta_type != _Const.NON_DEVICE):
                    self.__ses_attributes['pp_atta_sas_addr'] = port['link'].atta_wwn
                if ((port['id'] == 1 or port['id'] == "ep") and
                        port['link'].atta_type != _Const.NON_DEVICE):
                    self.__ses_attributes['ep_atta_sas_addr'] = port['link'].atta_wwn
        return self.__ses_attributes


class _Enclosure(object):

    def __init__(self, cfg):
        self.__cfg = cfg
        self.__expanders = []
        self.__drv = []
        self.name = cfg['name']
        encl = self.__cfg['enclosure']
        self.__type = encl['type']

        self.__process_exp(encl['expanders'], self.__type)
        self.__process_drive(encl['drives'])

        # for exp in self.__expanders: exp.print_link()
        # for drv in self.__drv: drv.print_link()

    def __process_drive(self, drvs):
        """
            Create drives under enclosure and add links between drive and
            expander under enclosure.
            drvs: list of drv_templates. user can define mutiple drive templates
            within an enclosure.
        """
        for drv_template in drvs:
            number = drv_template.pop('repeat', None)
            if number is None:
                number = 1
            _SNGenerator.reset(drv_template.pop('serial', None))
            slot_number = drv_template['slot_number']
            start_phy_id = drv_template.pop(
                'start_phy_id', _Const.DEFAULT_EXP_START_PHY)
            for index in range(0, number):
                drv_slot_id = index + slot_number
                drv = _Drv(drv_template, drv_slot_id)
                self.__drv.append(drv)
                phy_id = index + slot_number + start_phy_id
                drv.connect(_Link(0, 1, _Const.EXP_DEVICE, phy_id,
                                  self.__expanders[0].get_wwn(phy_id),
                                  self.__expanders[0].get_dev_name()
                                  ))
                drv.connect(_Link(1, 1, _Const.EXP_DEVICE, phy_id,
                                  self.__expanders[1].get_wwn(phy_id),
                                  self.__expanders[1].get_dev_name()))
                self.__expanders[0].connect(_Link(phy_id, 1, _Const.END_DEVICE,
                                                  0, drv.get_wwn(0),
                                                  drv.get_dev_name(),
                                                  drv_slot_id))
                self.__expanders[1].connect(_Link(phy_id, 1, _Const.END_DEVICE,
                                                  1, drv.get_wwn(1),
                                                  drv.get_dev_name(),
                                                  drv_slot_id))

    def __process_exp(self, exps, dae_type):
        """
            append expanders configured under the enclosure to its exp list
            exps: list of expanders under enclosure's configuration
            dae_type: enclosure's type
        """
        for e in exps:
            self.__expanders.append(_Expander(e, dae_type))

    def find_exp(self, exp_name):
        """
            get expander object under enclosure by its name
            exp_name: expander's "name" attribute, e.g. "lcc-a"

            return: expander object. return None if not found.
        """
        for _exp in self.__expanders:
            if _exp.name == exp_name:
                return _exp
        return None

    def find_expander_by_wwn(self, wwn):
        """
            get expander object under enclosure by its wwn
            exp_name: expander's "wwn" attribute

            return: expander object. return None if not found.
        """
        for _exp in self.__expanders:
            if _exp.get_wwn() == wwn:
                return _exp
        return None

    def find_drv(self, dev_name):
        """
            get drive object under enclosure by its device name (base wwn)
            dev_name: drive's base wwn

            return: drive object. return None if not found.
        """
        for d in self.__drv:
            if d.get_dev_name() == dev_name:
                return d
        return None

    def reset_for_traversal(self):
        """
            reset visited flag to False for each expander under the enclosure
        """
        for _exp in self.__expanders:
            _exp.set_visited(False)


class _DAEController(object):
    def __init__(self, cfg):
        self.__cfg = cfg
        self.__encl = []
        self.__process_enclosure()

    def __process_enclosure(self):
        """
            process enclosures under a disk_array. build connections under disk
            array.
        """
        for encl in self.__cfg['disk_array']:
            if 'enclosure' in encl:
                self.__encl.append(_Enclosure(encl))

        for encl in self.__cfg['disk_array']:
            if 'connections' in encl:
                self.__build_internal_connection(encl['connections'])

    def __build_internal_connection(self, links):
        """
            process internal connection inside disk array.
        """
        for link in links:
            link = link['link']
            exp0 = self.find_enclosure(
                link[0]['disk_array']).find_exp(link[0]['exp'])
            exp1 = self.find_enclosure(
                link[1]['disk_array']).find_exp(link[1]['exp'])

            exp0.connect(
                _Link(
                    link[0]['phy'],
                    link[0]['number'],
                    _Const.EXP_DEVICE,
                    link[1]['phy'],
                    exp1.get_wwn(),
                    exp1.get_dev_name()))
            exp1.connect(
                _Link(
                    link[1]['phy'],
                    link[1]['number'],
                    _Const.EXP_DEVICE,
                    link[0]['phy'],
                    exp0.get_wwn(),
                    exp0.get_dev_name()))

    def find_enclosure(self, encl_name):
        """
            get enclosure object under the disk_array by its name
        """
        for encl in self.__encl:
            if encl.name == encl_name:
                return encl
        return None

    def find_expander(self, wwn):
        """
            get expander object under the disk_array by its wwn
        """
        for encl in self.__encl:
            _exp = encl.find_expander_by_wwn(wwn)
            if _exp is not None:
                return _exp
        return None

    def find_drv(self, dev_name):
        """
           get drive object under the disk_array by its device_name
        """
        for encl in self.__encl:
            drv = encl.find_drv(dev_name)
            if drv is not None:
                return drv
        return None

    def reset_for_traversal(self):
        """
            reset visited flag to False for all expanders in the disk array
        """
        for encl in self.__encl:
            encl.reset_for_traversal()


class DAEProcessHelper(object):
    def __init__(self, cfg, ws_folder):
        self.__cfg = cfg
        self.__ws_folder = ws_folder
        self.__dae_arrays = []
        self.__process_disk_array()
        self.__process_connector()

    def __process_disk_array(self):
        """
            process disk_arrays and remove original disk_array dictionary from
            configuration
        """
        for obj in self.__cfg[:]:
            if obj.get('type', None) == "disk_array":
                self.__dae_arrays.append(_DAEController(obj))
                self.__cfg.remove(obj)

    def __find_exp(self, encl_name, exp_name):
        """
            find expander by the enclosure it belongs to and name
            encl_name: name of enclosure
            exp_name: name of expander

            return:
            _array: disk array that contains the given enclosure, expander pair
            _exp: enpander object
        """
        for _array in self.__dae_arrays:
            _encl = _array.find_enclosure(encl_name)
            if _encl is not None:
                _exp = _encl.find_exp(exp_name)
                return _array, _exp
        return None, None

    def __fill_external_connector(self, link):
        """
            update the expander's port link that is linked to an external
            controller, and append it to the expander's link list.
            link: the link from external_connectors
        """

        _, exp = self.__find_exp(link['atta_enclosure'], link['atta_exp'])
        for link_port in exp.get_port_link():
            if link_port['id'] == link['atta_port']:
                tmp = link_port['link']
                tmp.update_link(_Const.ACTIVE_DEVICE,
                                link['phy'], link['wwn'], link['wwn'])
                exp.connect(tmp)

    def __traversal(self, seses_dict, port_index, link, scsi_id_index):
        """
            traverse through a port of controller and fill in expanders
            information attached to it.
            seses_dict: list containing all seses' attributes
            port_index: controller's port
            link: connection information of the port
            scsi_id_index: start scsi id for the traversal

            return:
            a dictionary with all information under this port
        """
        encl, exp = self.__find_exp(link['atta_enclosure'], link['atta_exp'])
        # add connection to HBA.
        for link_port in exp.get_port_link():
            if link_port['id'] == link['atta_port']:
                tmp = link_port['link']
                tmp.update_link(_Const.HBA_DEVICE,
                                link['phy'], link['wwn'], link['wwn'])
                exp.connect(tmp)

        # add sub items under expander.
        ret = {
            "phy": link['phy'],
            "phy_number": tmp.num,
            "atta_type": _Const.EXP_DEVICE,
            "atta_phy": tmp.phy,
            "atta_wwn": exp.get_wwn(
                tmp.phy),
            "expanders": exp.traversal(
                seses_dict,
                port_index,
                encl,
                scsi_id_index)}

        return ret

    def __list_drv_nodes(self, nodes):
        """
            get all drives along with their attachment information associated
            with a port on controller.
            nodes: dictionary of information on the controller's certain port

            return: list of drvs connected to the port either directly or
            indirectly
        """
        drvs = []
        for exp in nodes["expanders"]:
            for link in exp['links']:
                if link['atta_type'] == _Const.END_DEVICE:
                    for _array in self.__dae_arrays:
                        drv = _array.find_drv(link['atta_dev_name'])
                        if drv is not None:
                            copy_drv = drv.get_port_cfg(link['atta_phy'])
                            _scsi_id = exp['start_scsi_id'] + link['phy']
                            drvs.append(copy_drv)
                            copy_drv['scsi-id'] = _scsi_id
                            link['atta_scsi_id'] = _scsi_id
                            break
                if link['atta_type'] == _Const.SES_DEVICE:
                    _scsi_id = exp['start_scsi_id'] + link['phy']
                    link['atta_scsi_id'] = _scsi_id
        return drvs

    def __process_connector(self):
        """
            iterate through all controllers in the configuration, setup links
            under each port of controller.
        """
        index = 0
        for controller in self.__cfg:
            for _item in self.__dae_arrays:
                _item.reset_for_traversal()
            seses_dict = []
            if 'connectors' in controller:
                hba_links = []
                file_name = "{0}/etc/diskarray{1}.json".format(
                    self.__ws_folder, index)
                controller['dae_file'] = file_name
                controller['drives'] = []
                scsi_id_index = [0]
                for link in controller.pop('external_connectors', []):
                    # fill external link first.
                    self.__fill_external_connector(link)
                port_index = 0
                for link in controller['connectors']:
                    # fill connections to local hba port
                    result = self.__traversal(
                        seses_dict, port_index, link, scsi_id_index)
                    for hba_link in hba_links:
                        if _Const.check_range_conflict(
                                result['phy'],
                                result['phy_number'],
                                hba_link['phy'],
                                hba_link['phy_number']):
                            raise Exception(
                                "HBA port duplicate use for phy {} to phy {}".format(
                                    result['phy'], result['phy'] + result['phy_number'] - 1))
                    link.update(result)
                    hba_links.append(
                        {"phy": result['phy'], "phy_number": result['phy_number']})
                    controller['drives'].extend(self.__list_drv_nodes(result))
                    port_index = port_index + 1
                controller['seses'] = seses_dict
            index = index + 1

    def create_dae_node(self, args):
        """
            dump a controller's port connection information and drive list to
            a json file, which will be parsed to qemu command line.
            args[0]: drive option list under a controller
            args[1]: controller's configuration in dictionary
        """
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
        filename = controller_info['dae_file']
        with open(filename, "w") as f:
            json.dump(_o, f, indent=2)
