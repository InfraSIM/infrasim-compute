'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import time
import sys
import hashlib
import re
import json
import socket
import multiprocessing
import types
import string
import random
import subprocess
import struct
import paramiko
from functools import wraps
from ctypes import cdll
from socket import AF_INET, AF_INET6, inet_ntop
from ctypes import (
    Structure, Union, POINTER,
    pointer, get_errno, cast,
    c_ushort, c_byte, c_void_p,
    c_char_p, c_uint, c_uint16,
    c_uint32
)
from infrasim import InfraSimError, run_command
from . import logger
from functools import reduce


libc = cdll.LoadLibrary('libc.so.6')
setns = libc.setns

# From linux/socket.h
AF_UNIX = 1

SIOCGIFCONF = 0x8912
SIOCGIFADDR = 0x8915


def check_kvm_existence():
    if os.path.exists("/dev/kvm"):
        return True
    return False


def fetch_image(url, checksum, dst):
    """
    :param url: Download link of the image file
    :param checksum: MD5 checksum of the image
    :param dst: Location to store the image
    """
    if os.path.exists(dst):
        if hashlib.md5(open(dst, "rb").read()).hexdigest() == checksum:
            return
        else:
            os.remove(dst)
    os.system("wget -c {0} -O {1}".format(url, dst))
    if hashlib.md5(open(dst, "rb").read()).hexdigest() != checksum:
        raise InfraSimError("Fail to download image {}".format(dst.split('/')[-1]))


def run_in_namespace(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        namespace = None
        try:
            namespace = getattr(args[0], "netns")
        except Exception:
            namespace = kwargs.get("netns")

        if namespace:
            with Namespace(nsname=namespace):
                ret = func(*args, **kwargs)

        else:
            ret = func(*args, **kwargs)
        return ret

    return wrapper


def get_interface_ip(ifname):
    """
    Get IP address given a interface name
    :param interface: interface name
    :return: empty string if no such interface, else IP address
    """
    interfaces = _get_all_interfaces()

    for intf_obj in interfaces:
        if intf_obj.get_interface_name() == ifname:
            return intf_obj.get_interface_ipv4_address()
    return None


class struct_ifaddrs(Structure):
    pass


class struct_sockaddr(Structure):
    _fields_ = [
        ('sa_family', c_ushort),
        ('sa_data', c_byte * 14), ]


class union_ifa_ifu(Union):
    _fields_ = [
        ('ifu_broadaddr', POINTER(struct_sockaddr)),
        ('ifu_dstaddr', POINTER(struct_sockaddr)), ]


class struct_sockaddr_in(Structure):
    _fields_ = [
        ('sin_family', c_ushort),
        ('sin_port', c_uint16),
        ('sin_addr', c_byte * 4)]


class struct_sockaddr_in6(Structure):
    _fields_ = [
        ('sin6_family', c_ushort),
        ('sin6_port', c_uint16),
        ('sin6_flowinfo', c_uint32),
        ('sin6_addr', c_byte * 16),
        ('sin6_scope_id', c_uint32)]


struct_ifaddrs._fields_ = [
    ('ifa_next', POINTER(struct_ifaddrs)),
    ('ifa_name', c_char_p),
    ('ifa_flags', c_uint),
    ('ifa_addr', POINTER(struct_sockaddr)),
    ('ifa_netmask', POINTER(struct_sockaddr)),
    ('ifa_ifu', union_ifa_ifu),
    ('ifa_data', c_void_p), ]


def getfamaddr(sa):
    family = sa.sa_family
    addr = None
    if family == AF_INET:
        sa = cast(pointer(sa), POINTER(struct_sockaddr_in)).contents
        addr = inet_ntop(family, sa.sin_addr)
    elif family == AF_INET6:
        sa = cast(pointer(sa), POINTER(struct_sockaddr_in6)).contents
        addr = inet_ntop(family, sa.sin6_addr)
    return family, addr


class NetworkInterface(object):

    def __init__(self, name):
        self.name = name
        self.index = libc.if_nametoindex(name)
        self.addresses = {}

    def __str__(self):
        return "%s [index=%d, IPv4=%s, IPv6=%s]" % (
            self.name, self.index,
            self.addresses.get(AF_INET),
            self.addresses.get(AF_INET6))

    def get_interface_name(self):
        return self.name

    def get_interface_ipv4_address(self):
        return self.addresses.get(AF_INET)

    def get_interface_ipv6_address(self):
        return self.addresses.get(AF_INET6)

    def get_interface_index(self):
        return self.index


def ifap_iter(ifap):
    ifa = ifap.contents
    while True:
        yield ifa
        if not ifa.ifa_next:
            break
        ifa = ifa.ifa_next.contents


def _get_all_interfaces():
    ifap = POINTER(struct_ifaddrs)()
    result = libc.getifaddrs(pointer(ifap))
    if result != 0:
        raise OSError(get_errno())
    del result

    try:
        retval = {}
        for ifa in ifap_iter(ifap):
            name = ifa.ifa_name
            i = retval.get(name)
            if not i:
                i = retval[name] = NetworkInterface(name)

            try:
                family, addr = getfamaddr(ifa.ifa_addr.contents)
                if addr:
                    i.addresses[family] = addr

            except Exception as e:
                logger.error(e)
                logger.info("-------> {}".format(i))

        return retval.values()
    finally:
        libc.freeifaddrs(ifap)


def get_all_interfaces():
    intf_list = []
    all_interfaces = _get_all_interfaces()
    for interface in all_interfaces:
        intf_list.append(interface.get_interface_name())

    return intf_list


@run_in_namespace
def ip4_addresses(netns=None):
    ip_list = []
    for intf_name in get_all_interfaces():
        if intf_name.startswith("ovs"):
            continue

        ip_addr = get_interface_ip(intf_name)
        if ip_addr is None:
            continue

        ip_list.append(ip_addr)

    return ip_list


def check_if_port_in_use(address, port):
    """
    True if port in use, false if not in use
    """
    s = socket.socket()
    try:
        s.connect((address, port))
        s.close()
        return True
    except socket.error:
        s.close()
        return False


def get_ns_path(nspath=None, nsname=None, nspid=None):
    if nsname:
        nspath = '/var/run/netns/%s' % nsname
    elif nspid:
        nspath = '/proc/%d/ns/net' % nspid

    return nspath


class Namespace(object):

    def __init__(self, nsname=None, nspath=None, nspid=None):
        self.mypath = get_ns_path(nspid=os.getpid())
        self.targetpath = get_ns_path(nspath,
                                      nsname=nsname,
                                      nspid=nspid)

        if not os.path.exists(self.targetpath):
            raise InfraSimError('invalid namespace {}'.format(nsname))

    def __enter__(self):
        self.myns = open(self.mypath)
        with open(self.targetpath) as fd:
            setns(fd.fileno(), 0)

    def __exit__(self, *args):
        setns(self.myns.fileno(), 0)
        self.myns.close()


def double_fork(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        # Create a queue to receive wrapped function's return value
        # and keep return to someone call the function
        p_r, p_s = multiprocessing.Pipe(False)

        # do the UNIX double-fork magic, see Stevens' "Advanced
        # Programming in the UNIX Environment" for details (ISBN 0201563177)
        try:
            pid = os.fork()
            if pid > 0:
                rsp = p_r.recv()
                if "ret" in rsp:
                    return rsp["ret"]
                elif "exception" in rsp:
                    raise rsp["exception"]
        except OSError as e:
            print >> sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
            sys.exit(1)

        os.setsid()

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                os._exit(os.EX_OK)
        except OSError as e:
            print >> sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
            sys.exit(1)

        try:
            ret = func(*args, **kwargs)
        except Exception as e:
            p_s.send({
                "exception": e
            })
        else:
            p_s.send({
                "ret": ret
            })

        os._exit(os.EX_OK)

    return wrapper


def try_func(times, func, *args, **kwargs):
    start = time.time()
    while True:
        try:
            return func(*args, **kwargs)
        except Exception:
            end = time.time()
            if end - start > times:
                break
    return False


def literal_string(s):
    char_backspace = re.compile("[^\b]\b")
    any_backspaces = re.compile("\b+")

    while True:
        t = char_backspace.sub("", s)
        for x in t:
            print x
        print "t = \n" + t
        if len(s) == len(t):
            return any_backspaces.sub("", t)
        s = t


def is_valid_ip(ip):
    '''
    [Function]: This function is to judge if ip is a valid IP, in str or int list
    [Input   ]: ip - the IP to judge, should be string or list
    [Output  ]: True - ip is valid
                False - ip is not valid
    '''

    if type(ip) in [types.StringType, types.UnicodeType]:
        p = re.search('^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$', ip)
        if p:
            for i in range(1, 5):
                if int(p.group(i), 0) not in range(0, 256):
                    return False
            return True
        else:
            return False
    elif isinstance(ip, types.ListType):
        if len(ip) != 4:
            return False
        else:
            for i in range(4):
                if isinstance(ip[i], types.IntType):
                    return False
                elif ip[i] not in range(0, 256):
                    return False
            return True
    else:
        return False


def random_serial(len=12):
    '''
    [Function]: Generate random serial number string, in upper case and digits
                for certain use
    [Input   ]: len - expected length of serial number string
    [Output  ]: A string in expected length
    '''
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(len))


def version_parser(expression):
    '''
    [Function]: Extract punctuaion and revision from an expression
    [Input   ]: expression - to be analyzed
    [Output  ]: Extracted punctuation and revision string
    '''
    # RE to match:
    #     >=, <=, ==, >, <
    p = re.compile(r"(?P<punctuation>[><=]=|[><])?\s*(?P<version>(\d+\.)*\d+)")
    m = p.search(expression)

    if m is None:
        return None, None

    return m.group("punctuation"), m.group("version")


def version_match(expression, runtime_version):
    '''
    [Function]: Given an expression in string to show expected version requirement,
                and a runtime version in string, return if runtime version meets
                the requirement
    [Input   ]: expression - requirement in string
                runtime_version - runtime version in string, in a form of "xx.xx.xx"
    [Output  ]: True - runtime version meets requirement
                False - fail to meet requirement
    '''
    p, v = version_parser(expression)

    if p is None or v is None:
        raise RuntimeError("Fail to identify version expression")

    v_target = v.split(".")
    v_runtime = runtime_version.split(".")
    v_diff = [int(r) - int(t) for t, r in zip(v_target, v_runtime)]
    symbol = 0
    for x in v_diff:
        if x != 0:
            symbol = x
            break
    if symbol > 0:
        if p in [">=", ">"]:
            return True
    elif symbol == 0:
        if p in [">=", "<=", "=="]:
            return True
    else:
        if p in ["<=", "<"]:
            return True

    return False


class qemu_version(object):
    '''
    [Function]: Decorator to check qemu version in certain tests, skip if version
                doesn't match, e.g.
                - @helper.qemu_version(">=2.10")
                - @helper.qemu_version("==2.6.2")
    '''

    def __init__(self, expression):
        self.expression = expression

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get QEMU runtime version
            str_result = run_command("qemu-system-x86_64 --version", True,
                                     subprocess.PIPE, subprocess.PIPE)[1]
            p = re.compile(r"(qemu_|version\s+)(?P<version>(\d+\.)*\d+)")
            m = p.search(str_result)
            qemu_version = m.group("version")
            if not version_match(self.expression, qemu_version):
                args[0].skipTest("Required qemu version: {}, runtime version: {}".
                                 format(self.expression, qemu_version))

            return func(*args, **kwargs)

        return wrapper


class NumaCtl(object):
    # Hyper-thread factor
    # If you open hyper-thread, it's basically set to 2
    HT_FACTOR = -1

    def __init__(self):
        """
        Build core map by reading /proc/cpuinfo
        """
        self._socket_list = []
        self._core_list = []
        self._core_map = {}
        self._core_map_avai = {}

        with open("/proc/cpuinfo", "r") as fp:
            lines = fp.readlines()

        core_block = []
        core_info = {}

        for line in lines:
            if len(line.strip()) != 0:
                key, value = line.split(":", 1)
                core_info[key.strip()] = value.strip()
            else:
                core_block.append(core_info)
                core_info = {}

        for core in core_block:
            for field in ["processor", "core id", "physical id"]:
                if field not in core:
                    err = "Error getting '{}' value from /proc/cpuinfo".format(field)
                    raise Exception(err)
                core[field] = int(core[field])

            if core["core id"] not in self._core_list:
                self._core_list.append(core["core id"])
            if core["physical id"] not in self._socket_list:
                self._socket_list.append(core["physical id"])
            key = (core["physical id"], core["core id"])
            if key not in self._core_map:
                self._core_map[key] = []
                self._core_map_avai[key] = []
            self._core_map[key].append(core["processor"])

            # Reserve first two core of each socket for system
            if key[1] in [0, 1]:
                self._core_map_avai[key].append(False)
            else:
                self._core_map_avai[key].append(True)

        self.__class__.HT_FACTOR = len(self._core_map[(0, 0)])

    def get_cpu_list(self, num):
        processor_use_up = True
        cpu_list = []
        assigned_count = 0
        socket_to_use = -1
        socket = None

        # Find available socket (with enough processor) to bind
        for socket in self._socket_list:
            count_avai = 0
            for core in self._core_list:
                for avai in self._core_map_avai[(socket, core)]:
                    if avai:
                        count_avai += 1
            if count_avai < num:
                continue
            else:
                socket_to_use = socket
                processor_use_up = False
                break
        if processor_use_up or socket_to_use < 0:
            raise Exception("All sockets don't have enough processor to bind.")

        # Append core which all HT processor are available
        for core in self._core_list:
            if num - assigned_count >= self.HT_FACTOR:
                # check if all processor are available on this core
                all_avai = reduce(lambda x, y: x and y,
                                  self._core_map_avai[(socket_to_use, core)])
                if all_avai:
                    cpu_list += self._core_map[(socket_to_use, core)]
                    self._core_map_avai[(socket_to_use, core)] = [False] * self.HT_FACTOR
                    assigned_count += self.HT_FACTOR
                    if num == assigned_count:
                        return cpu_list
            else:
                break

        # Use scattered core
        for core in self._core_list:
            # check availability of processors on this core
            core_avai_list = self._core_map_avai[(socket_to_use, core)]
            core_avai_count = len(filter(lambda x: x, core_avai_list))

            if num - assigned_count <= core_avai_count:
                # assign
                for i in range(self.HT_FACTOR):
                    if core_avai_list[i]:
                        cpu_list.append(self._core_map[(socket_to_use, core)][i])
                        self._core_map_avai[(socket_to_use, core)][i] = False
                        assigned_count += 1
                        if num == assigned_count:
                            return cpu_list

    def print_core_map(self):
        print "============================================================"
        print "Core and Socket Information (as reported by '/proc/cpuinfo')"
        print "============================================================\n"
        print "cores = ", self._core_list
        print "sockets = ", self._socket_list
        print ""

        max_processor_len = len(str(len(self._core_list) * len(self._socket_list) * self.HT_FACTOR - 1))
        max_core_map_len = max_processor_len * self.HT_FACTOR \
            + len('[, ]') + len('Socket ')
        max_core_id_len = len(str(max(self._core_list)))

        print " ".ljust(max_core_id_len + len('Core ')),
        for s in self._socket_list:
            print "Socket %s" % str(s).ljust(max_core_map_len - len('Socket ')),
        print ""
        print " ".ljust(max_core_id_len + len('Core ')),
        for s in self._socket_list:
            print "--------".ljust(max_core_map_len),
        print ""

        for c in self._core_list:
            print "Core %s" % str(c).ljust(max_core_id_len),
            for s in self._socket_list:
                print str(self._core_map[(s, c)]).ljust(max_core_map_len),
            print "\n"


class UnixSocket(object):

    def __init__(self, path):
        self.path = path
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        self.s.connect(self.path)

    def send(self, payload):
        logger.info("C:" + json.dumps(payload, indent=4).decode('string_escape'))
        self.s.send(payload)

    def recv(self):
        rsp = ""
        while True:
            snip = self.s.recv(1024)
            rsp += snip
            if len(snip) < 1024:
                break

        logger.info("S:" + json.dumps(rsp, indent=4).decode('string_escape'))
        return rsp

    def close(self):
        self.s.shutdown(2)
        self.s.close()


def port_forward(node):
    # Port forward from guest 22 to host 2222
    time.sleep(3)
    path = os.path.join(node.workspace.get_workspace(), ".monitor")
    s = UnixSocket(path)
    s.connect()
    s.recv()

    payload_enable_qmp = {
        "execute": "qmp_capabilities"
    }

    s.send(json.dumps(payload_enable_qmp))
    s.recv()

    payload_port_forward = {
        "execute": "human-monitor-command",
        "arguments": {
            "command-line": "hostfwd_add ::2222-:22"
        }
    }
    s.send(json.dumps(payload_port_forward))
    s.recv()

    s.close()
    time.sleep(3)


def prepare_ssh(ip_addr="127.0.0.1", port=2222):
    # wait until system is ready for ssh.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko.util.log_to_file("filename.log")
    try_func(600, paramiko.SSHClient.connect, ssh,
             ip_addr, port=port, username="root",
             password="root", timeout=120)
    return ssh


def fw_cfg_file_create(cfg_list, workspace):
    file_path = os.path.join(workspace, "data", "pci_topo_cfg")
    f = open(file_path, 'wb')
    sum = 0
    for cfg in cfg_list:
        bdf = cfg['bdf']
        sec_bus = cfg['sec_bus']
        bin_data = struct.pack('HBx', bdf, sec_bus)
        f.write(bin_data)
        sum = sum + ((bdf >> 8) & 0xff) + (bdf & 0xff) + sec_bus
    sum = (-sum) & 0xFF
    bin_sum = struct.pack('B', sum)
    f.write(bin_sum)
    f.close()
    return file_path


def get_ws_folder(element):
    parent = element.owner
    while parent and not hasattr(parent, "get_workspace"):
        parent = parent.owner

    ws = None
    if hasattr(parent, "get_workspace"):
        ws = parent.get_workspace()

    if ws is None or not os.path.exists(ws):
        ws = ""
    return ws
