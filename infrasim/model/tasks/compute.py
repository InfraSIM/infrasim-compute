'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-


import os
import time
import uuid
from infrasim import CommandRunFailed, ArgsNotCorrect, CommandNotFound
from infrasim import run_command, has_option
from infrasim import helper, config
from infrasim.helper import run_in_namespace, NumaCtl
from infrasim.model.core.task import Task
from infrasim.model.core.element import CElement
from infrasim.model.elements.chardev import CCharDev
from infrasim.model.elements.cpu import CCPU
from infrasim.model.elements.memory import CMemory
from infrasim.model.elements.backend import CBackendStorage
from infrasim.model.elements.backend import CBackendNetwork
from infrasim.model.elements.ipmi import CIPMI
from infrasim.model.elements.pci_topo import CPCITopologyManager
from infrasim.model.elements.fw_cfg import CPCIEFwcfg
from infrasim.model.elements.pcie_topology import CPCIETopology
from infrasim.model.elements.qemu_monitor import CQemuMonitor
from infrasim.model.elements.machine import CMachine


class CCompute(Task, CElement):

    numactl = None

    def __init__(self, compute_info):
        super(CCompute, self).__init__()
        CElement.__init__(self)
        self.__compute = compute_info
        self.__element_list = []
        self.__enable_kvm = True
        self.__smbios = None
        self.__bios = None
        self.__boot_order = None
        self.__boot_menu = None
        self.__boot_splash_name = None
        self.__boot_splash_time = None
        self.__qemu_bin = "qemu-system-x86_64"
        self.__cdrom_file = None
        self.__vendor_type = None
        # remember cpu object
        self.__cpu_obj = None
        self.__numactl_info = False
        self.__numactl_mode = None
        self.__cdrom_file = None
        self.__display = None

        # Node wise attributes
        self.__port_qemu_ipmi = 9002
        self.__socket_serial = ""
        self.__sol_enabled = False
        self.__kernel = None
        self.__initrd = None
        self.__cmdline = None
        self.__mem_path = None
        self.__extra_option = None
        self.__monitor = None
        self.__enable_monitor = False

        self.__force_shutdown = None

    def enable_sol(self, enabled):
        self.__sol_enabled = enabled

    def set_type(self, vendor_type):
        self.__vendor_type = vendor_type

    def set_port_qemu_ipmi(self, port):
        self.__port_qemu_ipmi = port

    def enable_qemu_monitor(self):
        self.__enable_monitor = True

    def set_socket_serial(self, o):
        self.__socket_serial = o

    def set_smbios(self, smbios):
        self.__smbios = smbios

    def get_smbios(self):
        return self.__smbios

    @run_in_namespace
    def precheck(self):
        # check if qemu-system-x86_64 exists
        try:
            run_command("which {}".format(self.__qemu_bin))
        except CommandRunFailed:
            self.logger.exception("[Compute] Can not find file {}".format(self.__qemu_bin))
            raise CommandNotFound(self.__qemu_bin)

        # check if smbios exists
        if not os.path.isfile(self.__smbios):
            raise ArgsNotCorrect("[Compute] Target SMBIOS file doesn't exist: {}".
                                 format(self.__smbios))

        if self.__kernel and os.path.exists(self.__kernel) is False:
            raise ArgsNotCorrect("[Compute] Kernel {} does not exist.".
                                 format(self.__kernel))

        if self.__initrd and os.path.exists(self.__initrd) is False:
            raise ArgsNotCorrect("[Compute] Kernel {} does not exist.".
                                 format(self.__initrd))

        # check if VNC port is in use
        if helper.check_if_port_in_use("0.0.0.0", self.__display + 5900):
            raise ArgsNotCorrect("[Compute] VNC port {} is already in use.".
                                 format(self.__display + 5900))

        # check sub-elements
        for element in self.__element_list:
            element.precheck()

        if 'boot' in self.__compute:
            if 'menu' in self.__compute['boot']:
                if isinstance(self.__compute['boot']['menu'], str):
                    menu_option = str(self.__compute['boot']['menu']).strip(" ").lower()
                    if menu_option not in ["on", "off"]:
                        msg = "[Compute] Error: illegal config option. " \
                              "The 'menu' must be either 'on' or 'off'."
                        raise ArgsNotCorrect(msg)
                elif not isinstance(self.__compute['boot']['menu'], bool):
                    msg = "[Compute] Error: illegal config option. The 'menu' " \
                          "must be either 'on' or 'off'."
                    raise ArgsNotCorrect(msg)

        # check kvm enabled is bool
        if self.__enable_kvm is not True and self.__enable_kvm is not False:
            raise ArgsNotCorrect("[Compute] KVM enabled is not a boolean: {}".
                                 format(self.__enable_kvm))

    @run_in_namespace
    def init(self):
        if not helper.check_kvm_existence():
            self.__enable_kvm = False
        else:
            self.__enable_kvm = self.__compute.get('kvm_enabled', True)

        if 'smbios' in self.__compute:
            self.__smbios = self.__compute['smbios']
        elif self.get_workspace():
            self.__smbios = os.path.join(self.get_workspace(),
                                         "data",
                                         "{}_smbios.bin".
                                         format(self.__vendor_type))
        else:
            self.__smbios = os.path.join(config.infrasim_data,
                                         "{0}/{0}_smbios.bin".format(self.__vendor_type))

        self.__bios = self.__compute.get('bios')
        if 'boot' in self.__compute:
            self.__boot_order = self.__compute['boot'].get('boot_order', "ncd")
            if 'menu' in self.__compute['boot']:
                self.__boot_menu = "on" if self.__compute['boot']['menu'] in [True, 'on'] else "off"
            self.__boot_splash_name = self.__compute['boot'].get('splash', None)
            self.__boot_splash_time = self.__compute['boot'].get('splash-time', None)
        else:
            self.__boot_order = "ncd"

        self.__cdrom_file = self.__compute.get('cdrom')

        self.__numactl_info = self.__compute.get("numa_control")
        if self.__numactl_info and os.path.exists("/usr/bin/numactl"):
            self.__numactl_mode = self.__numactl_info.get("mode", "auto")
            if self.__class__.numactl is None:
                self.__class__.numactl = NumaCtl()

            self.logger.info('[compute] infrasim has '
                             'enabled numa control')
        else:
            self.logger.info('[compute] infrasim can\'t '
                             'find numactl in this environment')

        self.__display = self.__compute.get('vnc_display', 1)
        self.__kernel = self.__compute.get('kernel')
        self.__initrd = self.__compute.get('initrd')

        self.__cmdline = self.__compute.get("cmdline")

        self.__mem_path = self.__compute.get("mem_path")
        self.__machine = self.__compute.get("machine")

        self.__extra_option = self.__compute.get("extra_option")
        self.__qemu_bin = self.__compute.get("qemu_bin", self.__qemu_bin)
        self.__force_shutdown = self.__compute.get("force_shutdown", True)

        machine_obj = CMachine(self.__machine)
        machine_obj.logger = self.logger
        self.__element_list.append(machine_obj)

        cpu_obj = CCPU(self.__compute['cpu'])
        cpu_obj.logger = self.logger
        self.__element_list.append(cpu_obj)
        self.__cpu_obj = cpu_obj

        memory_obj = CMemory(self.__compute['memory'])
        memory_obj.logger = self.logger
        self.__element_list.append(memory_obj)

        # If PCI device wants to sit on one specific PCI bus, the bus should be
        # created first prior to using the bus, here we always create the PCI
        # bus prior to other PCI devices' creation
        pci_topology_manager_obj = None
        if 'pci_bridge_topology' in self.__compute:
            pci_topology_manager_obj = CPCITopologyManager(self.__compute['pci_bridge_topology'])
            pci_topology_manager_obj.logger = self.logger
            self.__element_list.append(pci_topology_manager_obj)

        if 'pcie_topology' in self.__compute:
            pcie_topology_obj = CPCIETopology(self.__compute['pcie_topology'])
            pcie_topology_obj.logger = self.logger
            self.__element_list.append(pcie_topology_obj)
            if 'sec_bus' in str(self.__compute.get('pcie_topology')):
                fw_cfg_obj = CPCIEFwcfg()
                fw_cfg_obj.logger = self.logger
                fw_cfg_obj.set_workspace(self.get_workspace())
                pcie_topology_obj.set_fw_cfg_obj(fw_cfg_obj)
                self.__element_list.append(fw_cfg_obj)

        backend_storage_obj = CBackendStorage(self.__compute['storage_backend'])
        backend_storage_obj.logger = self.logger
        backend_storage_obj.owner = self
        if pci_topology_manager_obj:
            backend_storage_obj.set_pci_topology_mgr(pci_topology_manager_obj)
        backend_storage_obj.owner = self
        self.__element_list.append(backend_storage_obj)

        backend_network_obj = CBackendNetwork(self.__compute['networks'])
        backend_network_obj.logger = self.logger
        self.__element_list.append(backend_network_obj)

        if has_option(self.__compute, "ipmi"):
            ipmi_obj = CIPMI(self.__compute['ipmi'])
        else:
            ipmi_info = {
                'interface': 'kcs',
                'chardev': {
                    'backend': 'socket',
                    'host': '127.0.0.1',
                }
            }
            ipmi_obj = CIPMI(ipmi_info)
        ipmi_obj.logger = self.logger
        ipmi_obj.set_bmc_conn_port(self.__port_qemu_ipmi)
        self.__element_list.append(ipmi_obj)

        if self.__enable_monitor:
            self.__monitor = CQemuMonitor({
                'mode': 'control',
                'chardev': {
                    'backend': 'socket',
                    'path': os.path.join(self.get_workspace(), '.monitor'),
                    'server': True,
                    'wait': False
                }
            })
            self.__monitor.set_workspace(self.get_workspace())
            self.__monitor.logger = self.logger
            self.__element_list.append(self.__monitor)

        for element in self.__element_list:
            element.init()

    def get_commandline(self):
        # handle params
        self.handle_parms()

        qemu_commandline = ""
        for element_obj in self.__element_list:
            qemu_commandline = " ".join([qemu_commandline, element_obj.get_option()])

        qemu_commandline = " ".join([self.__qemu_bin, self.get_option(), qemu_commandline])

        # set cpu affinity
        if self.__numactl_mode == "auto":
            cpu_number = self.__cpu_obj.get_cpu_quantities()
            try:
                bind_cpu_list = [str(x) for x in self.__class__.numactl.get_cpu_list(cpu_number)]
            except Exception as e:
                bind_cpu_list = []
                self.logger.warning('[Compute] {}'.format(str(e)))
            if len(bind_cpu_list) > 0:
                numactl_option = 'numactl --physcpubind={} --localalloc'.format(','.join(bind_cpu_list))
                qemu_commandline = " ".join([numactl_option, qemu_commandline])
        elif self.__numactl_mode == "manual":
            bind_cpu_list = self.__numactl_info.get("cores").split(",")
            numactl_option = 'numactl --physcpubind={} --localalloc'.format(self.__numactl_info.get("cores"))
            mem_node_id = self.__numactl_info.get("node-id")
            if mem_node_id is not None:
                numactl_option = " ".join([numactl_option, "--membind={}".format(mem_node_id)])
            qemu_commandline = " ".join([numactl_option, qemu_commandline])

        return qemu_commandline

    def handle_parms(self):
        self.add_option("-vnc :{}".format(self.__display))
        self.add_option("-name {}".format(self.get_task_name()))
        self.add_option("-device sga")

        if self.__enable_kvm:
            self.add_option("--enable-kvm")

        if self.__smbios:
            self.add_option("-smbios file={}".format(self.__smbios))

        if self.__bios:
            self.add_option("-bios {}".format(self.__bios))

        if self.__mem_path:
            self.add_option("-mem-path {}".format(self.__mem_path))

        if self.__extra_option:
            self.add_option(self.__extra_option)

        boot_param = []
        if self.__boot_order:
            bootdev_path = self.get_workspace() + '/bootdev'
            if os.path.exists(bootdev_path) is True:
                with open(bootdev_path, "r") as f:
                    boot_param = f.readlines()
                boot_param[0] = boot_param[0].strip()
                if boot_param[0] == "default":
                    self.__boot_order = "c"
                elif boot_param[0] == "pxe":
                    self.__boot_order = "n"
                elif boot_param[0] == "cdrom":
                    self.__boot_order = "d"
                else:
                    self.__boot_order = "ncd"
                boot_param.append("order={}".format(self.__boot_order))
            else:
                boot_param.append("order={}".format(self.__boot_order))
        if self.__boot_menu:
            boot_param.append("menu={}".format(self.__boot_menu))
        if self.__boot_splash_name:
            boot_param.append("splash={}".format(self.__boot_splash_name))
        if self.__boot_splash_time:
            boot_param.append("splash-time={}".format(self.__boot_splash_time))
        tmp = ","
        self.add_option("-boot {}".format(tmp.join(boot_param)))

        if self.__cdrom_file:
            self.add_option("-cdrom {}".format(self.__cdrom_file))

        if self.__socket_serial and self.__sol_enabled:
            chardev = CCharDev({
                "backend": "socket",
                "path": self.__socket_serial,
                "wait": "off"
            })
            chardev.logger = self.logger
            chardev.set_id("serial0")
            chardev.init()
            chardev.handle_parms()

            self.add_option(chardev.get_option())
            self.add_option("-device isa-serial,chardev={}".format(chardev.get_id()))

        self.add_option("-uuid {}".format(str(uuid.uuid4())))

        if self.__kernel and self.__initrd:
            self.add_option("-kernel {} -initrd {}".format(self.__kernel, self.__initrd))

        if self.__cmdline:
            self.add_option("--append \"{}\"".format(self.__cmdline))

        for element_obj in self.__element_list:
            element_obj.handle_parms()

    # override Task.terminate, use monitor to shutdown qemu
    def terminate(self):
        if self.__force_shutdown:
            super(CCompute, self).terminate()
            return

        if self._task_is_running():
            self.__monitor.open()
            if self.__monitor.get_mode() == "readline":
                self.__monitor.send("system_powerdown\n")
            elif self.__monitor.get_mode() == "control":
                self.__monitor.send({"execute": "system_powerdown"})
            self.__monitor.close()

        start = time.time()
        while time.time() - start < 2 * 60:
            if not self._task_is_running():
                if os.path.exists(self.get_pid_file()):
                    os.remove(self.get_pid_file())
                break
            time.sleep(1)
        else:
            super(CCompute, self).terminate()
