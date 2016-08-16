#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author:  Robert Xia <robert.xia@emc.com>,
# Forrest Gu <Forrest.Gu@emc.com>

"""
This module majorly defines infrasim element models.
For each element class, they need to implement methods:

    - __init__()
        Get initialized with element information;
        Define element attributes;
        Assign default value for certain attributes;
    - init()
        Parse information dict, assign to all attribute;
    - precheck()
        Validate attribute integrity and environment compatibility;
    - handle_params()
        Add all attributes to command line options list;
    - get_option()
        Compose all options in list to a command line string;
"""


import fcntl
import time
import shlex
import subprocess
import os
import uuid
import signal
from . import logger, run_command, CommandRunFailed, ArgsNotCorrect

config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "config/chassis.yml")


class Utility(object):
    @staticmethod
    def execute_command(command):
        args = shlex.split(command)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=False)

        flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        time.sleep(1)
        errout = None
        try:
            errout = proc.stderr.readline()
        except IOError:
            pass

        if errout is not None:
            raise Exception("command {} failed. caused: {}".format(command, errout))
        return proc.pid

    @staticmethod
    def run_command(command):
        args = shlex.split(command)
        command_output = subprocess.check_output(args, shell=False)
        return command_output

    @staticmethod
    def get_working_directory():
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def ping_status(ip):
        rtn = True
        st = subprocess.call(['ping -c 3 %s >/dev/null' % ip], shell=True)
        if st:
            rtn = False
        return rtn


class CElement(object):
    def __init__(self):
        self.__option_list = []

    def precheck(self):
        raise NotImplemented("precheck is not implemented")

    def init(self):
        raise NotImplemented("init is not implemented")

    def handle_parms(self):
        raise NotImplemented("handle_parms is not implemented")

    def add_option(self, option):
        if option is None:
            return

        if option in self.__option_list:
            print "Warning: option {} already added.".format(option)
            return

        self.__option_list.append(option)

    def get_option(self):
        if len(self.__option_list) == 0:
            raise Exception("No option in the list")

        return " ".join(self.__option_list)


class CCPU(CElement):
    def __init__(self, cpu_info, socket_in_smbios=None):
        super(CCPU, self).__init__()
        self.__cpu = cpu_info
        self.__type = "host"
        self.__features = "+vmx"
        self.__quantities = 2
        self.__socket = socket_in_smbios

    def get_cpu_quantities(self):
        return self.__quantities

    def precheck(self):
        """
        Check if the CPU quantities exceeds the real physical CPU cores
        """
        if self.__quantities <= 0:
            raise ArgsNotCorrect(
                '[model:cpu] quantities invalid: {}, should be positive'.
                format(self.__quantities))

        if self.__quantities % self.__socket != 0:
            raise ArgsNotCorrect(
                '[model:cpu] quantities: {} is not divided by socket: {}'.
                format(self.__quantities, self.__socket))

    def init(self):
        if 'type' in self.__cpu:
            self.__type = self.__cpu['type']

        if 'quantities' in self.__cpu:
            self.__quantities = self.__cpu['quantities']

        if 'features' in self.__cpu:
            self.__features = self.__cpu['features']

        if self.__socket is None:
            self.__socket = 2

    def handle_parms(self):
        if self.__features:
            cpu_option = "-cpu {0},{1}".format(self.__type, self.__features)
        else:
            cpu_option = "-cpu {}".format(self.__type)

        self.add_option(cpu_option)

        cores = self.__quantities / self.__socket
        smp_option = "-smp {vcpu_num},sockets={socket},cores={cores},threads=1".format(
                vcpu_num=self.__quantities, socket=self.__socket, cores=cores)

        self.add_option(smp_option)


class CMemory(CElement):
    def __init__(self, memory_info):
        super(CMemory, self).__init__()
        self.__memory = memory_info
        self.__memory_size = None

    def precheck(self):
        """
        Check if the memory size exceeds the system available size
        """
        pass

    def init(self):
        if 'size' in self.__memory:
            self.__memory_size = self.__memory['size']
        else:
            raise Exception("ERROR: please set the memory size")

    def handle_parms(self):
        memory_option = "-m {}".format(self.__memory_size)
        self.add_option(memory_option)


class CDrive(CElement):
    def __init__(self, drive_info):
        super(CDrive, self).__init__()
        self.__drive = drive_info
        self.__index = None
        self.__bus = "sata"  # ide/sata/scsi
        self.__vendor = None
        self.__model = None
        self.__serial = None
        self.__product = None
        self.__version = None
        self.__bootindex = None
        self.__cache = "writeback"  # none/writeback/writethrough
        self.__aio = None  # threads/native
        self.__file = None
        self.__rotation = None
        self.__type = "file"
        self.__format = "qcow2"
        self.__bus_address = None
        self.__size = 8

    def set_index(self, index):
        self.__index = index

    def get_index(self):
        return self.__index

    def get_bus_type(self):
        return self.__bus

    def set_bus_address(self, addr):
        self.__bus_address = addr

    def precheck(self):
        """
        Check if the parition or drive file exists
        Check if the cache/aio parameters are valid
        """
        pass

    def init(self):
        # 'bus' would be one of three buses (ide, sata, scsi) in our case
        if 'bus' in self.__drive:
            self.__bus = self.__drive['bus']

        if 'type' in self.__drive:
            self.__type = self.__drive['type']

        if 'bootindex' in self.__drive:
            self.__bootindex = self.__drive['bootindex']

        # for ide-hd drive, there is no vendor properties
        if 'vendor' in self.__drive and self.__bus == "scsi":
            self.__vendor = self.__drive['vendor']

        if 'serial' in self.__drive:
            self.__serial = self.__drive['serial']

        if 'model' in self.__drive:
            self.__model = self.__drive['model']

        if 'product' in self.__drive:
            self.__product = self.__drive['product']

        if 'version' in self.__drive:
            self.__version = self.__drive['version']

        if 'rotation' in self.__drive:
            self.__rotation = self.__drive['rotation']

        if 'format' in self.__drive:
            self.__format = self.__drive['format']

        if 'cache' in self.__drive:
            self.__cache = self.__drive['cache']

        if 'aio' in self.__drive:
            self.__aio = self.__drive['aio']

        if 'size' in self.__drive:
            self.__size = self.__drive['size']

        # If user announce drive file in config, use it
        # else create for them.
        if 'file' in self.__drive:
            self.__file = self.__drive['file']
            # assume the files starts with "/dev/" are block device
            # all the block devices are assumed to be raw format
            if self.__file.startswith("/dev/"):
                self.__format = "raw"
        else:
            disk_file_base = os.environ['HOME'] + '/.infrasim/'
            disk_file = disk_file_base + "sd{0}.img".format(chr(97+self.__index))
            if not os.path.exists(disk_file):
                command = "qemu-img create -f qcow2 {0}sd{1}.img {2}G".\
                    format(disk_file_base, chr(97+self.__index), self.__size)
                try:
                    run_command(command)
                except CommandRunFailed as e:
                    raise e
            self.__file = disk_file

    def handle_parms(self):
        host_option = ""
        if self.__file:
            host_option = "file={}".format(self.__file)
        else:
            raise Exception("Please specify the file option for disk.")

        if self.__format:
            host_option = ",".join([host_option, "format={}".format(self.__format)])

        host_option = ",".join([host_option, "if={}".format("none")])
        host_option = ",".join([host_option, "id=drive{}".format(self.__index)])

        if self.__cache:
            host_option = ",".join([host_option, "cache={}".format(self.__cache)])

        if self.__aio and self.__cache == "none":
            host_option = ",".join([host_option, "aio={}".format(self.__aio)])

        device_option = ""

        # TODO:
        # Fixme: might be not correct here? need redesign?
        if self.__bus == "sata":
            device_option = "ide-hd"
        elif self.__bus == "scsi":
            device_option = "scsi-hd"
        else:
            device_option = "ide-hd"

        if self.__vendor:
            device_option = ",".join([device_option, "vendor={}".format(self.__vendor)])

        if self.__model:
            device_option = ",".join([device_option, "model={}".format(self.__model)])

        if self.__product:
            device_option = ",".join([device_option, "product={}".format(self.__product)])

        if self.__serial:
            device_option = ",".join([device_option, "serial={}".format(self.__serial)])

        if self.__version:
            device_option = ",".join([device_option, "ver={}".format(self.__version)])

        if self.__bootindex:
            device_option = ",".join([device_option, "bootindex={}".format(self.__bootindex)])

        if self.__rotation is not None:
            device_option = ",".join([device_option, "rotation={}".format(self.__rotation)])

        if self.__bus_address:
            device_option = ",".join([device_option, "bus={}".format(self.__bus_address)])

        device_option = ",".join([device_option, "drive=drive{}".format(self.__index)])

        drive_option = " ".join(["-drive", host_option,
                                "-device", device_option])

        self.add_option(drive_option)


class CBackendStorage(CElement):
    def __init__(self, drive_info_list):
        super(CBackendStorage, self).__init__()
        self.__backend_drive_list = drive_info_list
        self.__drive_list = []
        # Backend info table:
        # {
        #   'ahci': [drive1, drive2, drive3, ...],
        #   'lsi': [drive5, drive6, dirve7, ...],
        #   ...
        # }
        self.__backend_info = {}

        # {
        #   'lsi': {
        #       'max_drives': 8
        #       'address': lsi0
        #    }
        # }
        self.__controller_info = {}

        self.__max_disks_per_controller = 8

    def precheck(self):
        for drive_obj in self.__drive_list:
            drive_obj.precheck()

    def init(self):
        drive_index = 0
        for drive in self.__backend_drive_list:
            drive_obj = CDrive(drive)
            drive_obj.set_index(drive_index)
            self.__drive_list.append(drive_obj)
            drive_index += 1

        for drive_obj in self.__drive_list:
            drive_obj.init()

        # TODO:
        # Fixme: might be not correct here? need redesign?
        controller = None
        for drive_obj in self.__drive_list:
            bus_type = drive_obj.get_bus_type()
            if bus_type == "sata":
                controller = "ahci"
            elif bus_type == "scsi":
                controller = "mptsas1068"
            elif bus_type == "ide":
                print "TBD here"
            else:
                print "ERROR: should not get here"

            if controller not in self.__backend_info:
                self.__backend_info[controller] = []

            self.__backend_info[controller].append(drive_obj)

        # TODO:
        # If users set multiple different kind of storage
        # controllers, how we handle such case? for example
        # If users configured one AHCI controller for SATADOM disks,
        # and configured one SAS controller for SAS disks.
        for k in self.__backend_info.keys():
            bus = "{}0".format(k)
            for drive in self.__backend_info[k]:
                bus_address = "{}.{}".format(bus, drive.get_index())
                drive.set_bus_address(bus_address)

    def handle_parms(self):
        # TODO:
        for k in self.__backend_info.keys():
            self.add_option("-device {},id={}0".format(k, k))

        for drive_obj in self.__drive_list:
            drive_obj.handle_parms()

        for drive_obj in self.__drive_list:
            self.add_option(drive_obj.get_option())


class CNetwork(CElement):
    def __init__(self, network_info):
        super(CNetwork, self).__init__()
        self.__network = network_info
        self.__network_list = []
        self.__network_mode = "nat"
        self.__bridge_name = None
        self.__nic_name = None
        self.__mac_address = None
        self.__index = 0

    def set_index(self, index):
        self.__index = index

    def precheck(self):
        # Check if parameters are valid
        # bridge exists?
        pass

    def init(self):
        if 'network_mode' in self.__network:
            self.__network_mode = self.__network['network_mode']

        if 'bridge' in self.__network:
            self.__bridge_name = self.__network['bridge']

        if 'device' in self.__network:
            self.__nic_name = self.__network['device']

        if 'mac' in self.__network:
            self.__mac_address = self.__network['mac']

    def handle_parms(self):
        if self.__mac_address is None:
            uuid_val = uuid.uuid4()
            str1 = str(uuid_val)[-2:]
            str2 = str(uuid_val)[-4:-2]
            str3 = str(uuid_val)[-6:-4]
            self.__mac_address = ":".join(["52:54:BE", str1, str2, str3])

        if self.__network_mode == "bridge":
            if self.__bridge_name is None:
                self.__bridge_name = "br0"

            netdev_option = ",".join(['bridge', 'id=netdev{}'.format(self.__index),
                                      'br={}'.format(self.__bridge_name),
                                      'helper=/usr/libexec/qemu-bridge-helper'])
            nic_option = ",".join(["{}".format(self.__nic_name),
                                   "netdev=netdev{}".format(self.__index),
                                   "mac={}".format(self.__mac_address)])

            network_option = " ".join(["-netdev {}".format(netdev_option),
                                       "-device {}".format(nic_option)])
        elif self.__network_mode == "nat":
            network_option = "-net user -net nic"
        else:
            raise Exception("ERROR: {} is not supported now.".format(self.__network_mode))

        self.add_option(network_option)


class CBackendNetwork(CElement):
    def __init__(self, network_info_list):
        super(CBackendNetwork, self).__init__()
        self.__backend_network_list = network_info_list

        self.__network_list = []

    def precheck(self):
        for network_obj in self.__network_list:
            network_obj.precheck()

    def init(self):
        index = 0
        for network in self.__backend_network_list:
            network_obj = CNetwork(network)
            network_obj.set_index(index)
            self.__network_list.append(network_obj)
            index += 1

        for network_obj in self.__network_list:
            network_obj.init()

    def handle_parms(self):
        for network_obj in self.__network_list:
            network_obj.handle_parms()

        for network_obj in self.__network_list:
            self.add_option(network_obj.get_option())


class CIPMI(CElement):
    def __init__(self, ipmi_info):
        super(CIPMI, self).__init__()
        self.__ipmi = ipmi_info
        self.__interface = None
        self.__host = None
        self.__bmc_connection_port = None

    def precheck(self):
        """
        Check if internal socket port is used.
        """
        pass

    def init(self):
        if 'interface' in self.__ipmi:
            self.__interface = self.__ipmi['interface']

        if 'host' in self.__ipmi:
            self.__host = self.__ipmi['host']

        if 'bmc_connection_port' in self.__ipmi:
            self.__bmc_connection_port = self.__ipmi['bmc_connection_port']

    def handle_parms(self):
        chardev_option = ','.join(["socket", 'id=ipmi0',
                                   'host={}'.format(self.__host),
                                   'port={}'.format(self.__bmc_connection_port),
                                   'reconnect=10'])
        bmc_option = ','.join(['ipmi-bmc-extern', 'chardev=ipmi0', 'id=bmc0'])
        interface_option = ','.join(['isa-ipmi-kcs', 'bmc=bmc0'])

        ipmi_option = " ".join(["-chardev {}".format(chardev_option),
                                "-device {}".format(bmc_option),
                                "-device {}".format(interface_option)])
        self.add_option(ipmi_option)


class Task(object):
    def __init__(self):
        # priroty should be range from 0 to 5
        # +-----+-----+-----+----+-----+
        # |  0  |  1  |  2  |  3 |  4  |
        # +-----+-----+-----+----+-----+
        # |High |                | Low |
        # +-----+-----+-----+----+-----+
        self.__task_priority = None
        self.__task_data = None
        self.__task_name = None
        self._node_id = None
        self.__debug = False

    def set_priority(self, priority):
        self.__task_priority = priority

    def get_priority(self):
        return self.__task_priority

    def set_task_name(self, name):
        self.__task_name = name

    def get_task_name(self):
        return self.__task_name

    def get_commandline(self):
        raise NotImplemented("get_commandline not implemented")

    def set_task_data(self, directory):
        self.__task_data = directory

    def get_task_data(self):
        return self.__task_data

    def set_node_id(self, node_id):
        self._node_id = node_id

    def get_task_pid(self):
        pid_file = "{}/.{}".format(self.__task_data, self.__task_name)
        try:
            with open(pid_file, "r") as f:
                pid = f.readline()
        except Exception:
            return None
        return pid.strip()

    def run(self):
        if self.__debug:
            print self.get_commandline()
            return

        pid = self.get_task_pid()
        if pid > 0:
            print "Task {} is already running. pid: {}".format(self.__task_name, pid)
            return

        pid = Utility.execute_command(self.get_commandline())
        print "task {} is running. pid {}".format(self.__task_name, pid)
        pid_file = "{}/.{}".format(self.__task_data, self.__task_name)
        with open(pid_file, "w") as f:
            f.write("{}".format(pid))

    def terminate(self):
        task_pid = self.get_task_pid()
        pid_file = "{}/.{}".format(self.__task_data, self.__task_name)
        try:
            if task_pid:
                print "Stop task {}, pid {}".format(self.__task_name, task_pid)
                os.kill(int(task_pid), signal.SIGTERM)
                time.sleep(1)
                if os.path.exists(pid_file):
                    os.remove(pid_file)
        except OSError:
            if os.path.exists(pid_file):
                os.remove(pid_file)
            print("stop task {} failed.".format(self.__task_name))

    def status(self):
        pid_file = "{}/.{}".format(self.__task_data, self.__task_name)
        if not os.path.exists(pid_file):
            print "Task {} is stopped.".format(self.__task_name)
        else:
            task_pid = self.get_task_pid()
            if task_pid:
                print "Task {} [ {} ] is running.".format(self.__task_name, task_pid)


class CCompute(Task, CElement):
    def __init__(self, compute_info):
        super(CCompute, self).__init__()
        CElement.__init__(self)
        self.__name = None
        self.__compute = compute_info
        self.__element_list = []
        self.__enable_kvm = True
        self.__smbios = None
        self.__bios = None
        self.__boot_order = "ncd"
        self.__qemu_bin = "qemu-system-x86_64"
        self.__serial = 9003
        self.__cdrom_file = None
        # remember cpu object
        self.__cpu_obj = None
        self.__numactl_obj = None

    def set_numactl(self, numactl_obj):
        self.__numactl_obj = numactl_obj

    def precheck(self):
        # check if qemu-system-x86_64 exists

        # check sub-elements
        for element in self.__element_list:
            element.precheck()

    def init(self):
        if 'name' in self.__compute:
            self.__name = self.__compute['name']
            self.set_task_name(self.__name)
        else:
            raise ArgsNotCorrect('[model:compute] compute name is not set')

        if 'kvm_enabled' in self.__compute:
            if self.__compute['kvm_enabled']:
                if os.path.exists("/dev/kvm"):
                    self.__enable_kvm = True
                    logger.log('[model:compute] infrasim has enabled kvm')
                else:
                    self.__enable_kvm = False
                    logger.warning('[model:compute] infrasim can\'t enable kvm on this environment')
            else:
                self.__enable_kvm = False
                logger.log('[model:compute] infrasim doesn\'t enable kvm')

        if 'smbios' in self.__compute:
            self.__smbios = self.__compute['smbios']
        elif os.path.exists("/usr/local/etc/infrasim/{0}/{0}_smbios.bin".format(self.__name)):
            self.__smbios = "/usr/local/etc/infrasim/{0}/{0}_smbios.bin".format(self.__name)
        else:
            logger.warning('[model:compute] infrasim doesn\'t find proper SMBIOS file')

        if 'bios' in self.__compute:
            self.__bios = self.__compute['bios']

        if 'boot_order' in self.__compute:
            self.__boot_order = self.__compute['boot_order']

        if 'cdrom' in self.__compute:
            self.__cdrom_file = self.__compute['cdrom']

        if 'serial' in self.__compute:
            self.__serial = self.__compute['serial']

        cpu_obj = CCPU(self.__compute['cpu'])
        self.__element_list.append(cpu_obj)
        self.__cpu_obj = cpu_obj

        memory_obj = CMemory(self.__compute['memory'])
        self.__element_list.append(memory_obj)

        backend_storage_obj = CBackendStorage(self.__compute['drives'])
        self.__element_list.append(backend_storage_obj)

        backend_network_obj = CBackendNetwork(self.__compute['networks'])
        self.__element_list.append(backend_network_obj)

        ipmi_obj = CIPMI({
            "interface": "kcs",
            "host": "127.0.0.1",
            "bmc_connection_port": 9002
        })
        self.__element_list.append(ipmi_obj)

        for element in self.__element_list:
            element.init()

    def get_commandline(self):
        # handle params
        self.handle_parms()

        qemu_commandline = ""
        for element_obj in self.__element_list:
            qemu_commandline = " ".join([element_obj.get_option(), qemu_commandline])

        qemu_commandline = " ".join([self.__qemu_bin, self.get_option(), qemu_commandline])

        # set cpu affinity
        if self.__numactl_obj:
            cpu_number = self.__cpu_obj.get_cpu_quantities()
            bind_cpu_list = [str(x) for x in self.__numactl_obj.get_cpu_list(cpu_number)]
            if len(bind_cpu_list) > 0:
                numactl_option = 'numactl --physcpubind={} --localalloc'.format(','.join(bind_cpu_list))
                qemu_commandline = " ".join(numactl_option, qemu_commandline)

        return qemu_commandline

    def handle_parms(self):
        self.add_option("-vnc :1")
        self.add_option("-name {}".format(self.get_task_name()))
        self.add_option("-device sga")

        if self.__enable_kvm:
            self.add_option("--enable-kvm")

        if self.__smbios:
            self.add_option("-smbios file={}".format(self.__smbios))

        if self.__bios:
            self.add_option("-bios {}".format(self.__bios))

        if self.__boot_order:
            self.add_option("-boot {}".format(self.__boot_order))

        self.add_option("-machine q35,usb=off,vmport=off")

        if self.__cdrom_file:
            self.add_option("-cdrom {}".format(self.__cdrom_file))

        self.add_option("-chardev socket,id=mon,host=127.0.0.1,port=2345,server,nowait ")

        self.add_option("-mon chardev=mon,id=monitor")

        if self.__serial:
            self.add_option("-serial mon:udp:127.0.0.1:{},nowait".format(self.__serial))

        self.add_option("-uuid {}".format(str(uuid.uuid4())))

        for element_obj in self.__element_list:
            element_obj.handle_parms()


class CBMC(Task):
    def __init__(self, bmc_info):
        super(CBMC, self).__init__()
        self.__bmc = bmc_info
        self.__address = 0x20
        self.__channel = 1
        self.__lan_interface = None
        self.__lancontrol_script = "scripts/lancontrol"
        self.__chassiscontrol_script = "scripts/chassiscontrol"
        self.__telnet_listen_port = None
        self.__compute_connection_port = None
        self.__startnow = False
        self.__poweroff_wait = 5
        self.__kill_wait = 1
        self.__username = None
        self.__password = None
        self.__emu_file = None

    def precheck(self):
        # check if ipmi_sim exists
        # check script exits
        # check ports are in use
        # check lan interface exists
        pass

    def write_bmc_config(self):
        default_vbmc_conf_file = "{}/vbmc.conf".format(self.get_task_data())

        conf_contents = []

        conf_contents.append("name \"{}\"\n".format(self.get_task_name()))
        conf_contents.append("set_working_mc {0:#04x}\n".format(self.__address))
        conf_contents.append("\tstartlan {}\n".format(self.__channel))
        conf_contents.append("\t\taddr :: 623\n")
        conf_contents.append("\t\tpriv_limit admin\n")
        conf_contents.append("\t\tallowed_auths_callback none md2 md5 straight\n")
        conf_contents.append("\t\tallowed_auths_user none md2 md5 straight\n")
        conf_contents.append("\t\tallowed_auths_operator none md2 md5 straight\n")
        conf_contents.append("\t\tallowed_auths_admin none md2 md5 straight\n")
        conf_contents.append("\t\tguid a123456789abcdefa123456789abcdef\n")
        conf_contents.append("\t\tlan_config_program \"{} {}\"\n".format(self.__lancontrol_script,
                                                                         self.__lan_interface))
        conf_contents.append("\tendlan\n")
        conf_contents.append("\tchassis_control \"{0} {1:#04x}\"\n".format(self.__chassiscontrol_script,
                                                                           self.__address))
        conf_contents.append("\tserial 15 0.0.0.0 {0} codec VM ipmb {1:#04x}\n".format(self.__compute_connection_port,
                                                                                       self.__address))
        conf_contents.append("\tstartcmd \"{}/startcmd\"\n".format(self.get_task_data()))
        conf_contents.append("\tconsole 0.0.0.0 {}\n".format(self.__telnet_listen_port))
        if self.__startnow:
            conf_contents.append("\tstartnow true\n")
        else:
            conf_contents.append("\tstartnow false\n")

        conf_contents.append("\tpoweroff_wait {}\n".format(self.__poweroff_wait))
        conf_contents.append("\tkill_wait {}\n".format(self.__kill_wait))
        conf_contents.append("\tuser 1 true \"\"\t\t\"test\"\t\tuser\t10\tnone md2 md5 straight\n")
        conf_contents.append("\tuser 2 true \"{}\"\t\"{}\"\t\tadmin\t10\tnone md2 md5 straight\n".format(
                                self.__username,
                                self.__password))

        with open(default_vbmc_conf_file, "w") as f:
            f.writelines(conf_contents)

    def init(self):
        if 'address' in self.__bmc:
            self.__address = self.__bmc['address']

        if 'channel' in self.__bmc:
            self.__channel = self.__bmc['channel']

        if 'interface' in self.__bmc:
            self.__lan_interface = self.__bmc['interface']

        if 'lancontrol' in self.__bmc:
            self.__lancontrol_script = self.__bmc['lancontrol']

        if 'chassiscontrol' in self.__bmc:
            self.__chassiscontrol_script = self.__bmc['chassiscontrol']

        if 'telnet_listen_port' in self.__bmc:
            self.__telnet_listen_port = self.__bmc['telnet_listen_port']

        if 'compute_connection_port' in self.__bmc:
            self.__compute_connection_port = self.__bmc['compute_connection_port']

        if 'startnow' in self.__bmc:
            self.__startnow = self.__bmc['startnow']

        if 'poweroff_wait' in self.__bmc:
            self.__poweroff_wait = self.__bmc['poweroff_wait']

        if 'kill_wait' in self.__bmc:
            self.__kill_wait = self.__bmc['kill_wait']

        if 'username' in self.__bmc:
            self.__username = self.__bmc['username']

        if 'password' in self.__bmc:
            self.__password = self.__bmc['password']

        if 'emu_file' in self.__bmc:
            self.__emu_file = self.__bmc['emu_file']

        self.write_bmc_config()

    def get_commandline(self):
        ipmi_cmd_str = "ipmi_sim -c {}/vbmc.conf -f {} -n".format(self.get_task_data(), self.__emu_file)
        return ipmi_cmd_str


class CSocat(Task):
    def __init__(self):
        pass


class CNode(object):
    def __init__(self, node_info):
        self.__tasks_list = []
        self.__node = node_info
        self.__name = None
        self.__node_id = None
        self.__numactl_obj = None

    def set_numactl(self, numactl_obj):
        self.__numactl_obj = numactl_obj

    def get_node_id(self):
        return self.__node_id

    def set_name(self, name):
        self.__name = name

    def precheck(self):
        for task in self.__tasks_list:
            task.precheck()

    def init(self):
        if self.__node['compute'] is None:
            raise Exception("No compute information")

        if self.__node['bmc'] is None:
            raise Exception("No BMC information")

        if 'node_id' in self.__node:
            self.__node_id = self.__node['node_id']

        compute_obj = CCompute(self.__node['compute'])
        compute_obj.set_priority(2)
        compute_obj.set_node_id(self.__node_id)
        compute_obj.set_numactl(self.__numactl_obj)
        compute_obj.set_task_name("{}-{}-node".format(self.__name, self.__node_id))
        self.__tasks_list.append(compute_obj)

        bmc_obj = CBMC(self.__node['bmc'])
        bmc_obj.set_priority(1)
        bmc_obj.set_task_name("{}-{}-bmc".format(self.__name, self.__node_id))
        self.__tasks_list.append(bmc_obj)

        for task in self.__tasks_list:
            task.set_task_data("chassis/node{}".format(self.__node_id))
            task.init()

    # Run tasks list as the priority
    def start(self):
        # sort the tasks as the priority
        self.__tasks_list.sort(key=lambda x: x.get_priority(), reverse=False)

        for task in self.__tasks_list:
            task.run()

    def stop(self):
        for task in self.__tasks_list:
            task.terminate()

    def status(self):
        for task in self.__tasks_list:
            task.status()


class CChassis(object):
    def __init__(self, chassis_info):
        self.__chassis = chassis_info
        self.__chassis_model = None
        self.__node_list = []
        self.__numactl_obj = NumaCtl()

    def precheck(self):
        # check total resources
        for node in self.__node_list:
            node.precheck()

    def init(self):
        for node in self.__chassis['nodes']:
            node_obj = CNode(node)
            node_obj.set_name(self.__chassis['name'])
            node_obj.set_numactl(self.__numactl_obj)
            self.__node_list.append(node_obj)

        for node_obj in self.__node_list:
            node_obj.init()

    def start(self, node_id=None):
        for node_obj in self.__node_list:
            if node_id and node_obj.get_node_id() == node_id:
                node_obj.start()
                return

        for node_obj in self.__node_list:
            node_obj.start()

    def stop(self, node_id=None):
        for node_obj in self.__node_list:
            if node_id and node_obj.get_node_id() == node_id:
                node_obj.stop()
                return

        for node_obj in self.__node_list:
            node_obj.stop()

    def status(self):
        for node_obj in self.__node_list:
            node_obj.status()


class NumaCtl(object):
    def __init__(self):
        self.__cpu_list = []
        self.__node_list = []
        self.__numactl_table = {}
        numactl_show_output = Utility.run_command("numactl --show")
        for line in numactl_show_output.split(os.linesep):
            if line.startswith("physcpubind:"):
                self.__cpu_list = [int(x) for x in line.split(':')[1].strip().split()]

            if line.startswith("nodebind:"):
                self.__node_list = [int(x) for x in line.split(':')[1].strip().split()]

        numactl_hardware_output = Utility.run_command("numactl --hardware")
        for node_index in self.__node_list:
            self.__numactl_table[node_index] = []
            for line in numactl_hardware_output.split(os.linesep):
                if line.startswith("node {} cpus:".format(node_index)):
                    self.__numactl_table[node_index] = [int(x) for x in line.split(':')[1].strip().split()]

    def get_cpu_list(self, num):
        for i in self.__node_list:
            if len(self.__numactl_table[i]) >= num:
                return [self.__numactl_table[i].pop() for _ in range(0, num)]

        returned_cpu_list = []
        for i in self.__node_list:
            while (len(self.__numactl_table[i])) > 0:
                returned_cpu_list.append(self.__numactl_table[i].pop())
                if len(returned_cpu_list) == num:
                    return returned_cpu_list

        return returned_cpu_list
