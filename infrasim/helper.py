'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import socket
from functools import wraps
from ctypes import cdll
import fcntl
import struct
import array
from infrasim import run_command, InfraSimError
from infrasim import logger

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
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ifreq = struct.pack('16sH14s', ifname, AF_UNIX, '\x00'*14)
        res = fcntl.ioctl(s.fileno(), SIOCGIFADDR, ifreq)
        ip = struct.unpack('16sH2x4s8x', res)[2]
        s.close()
        return socket.inet_ntoa(ip)
    except Exception:
        return None


def get_all_interfaces():
    bytes = 128 * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interface_names = array.array('B', '\0' * bytes)
    inbytes = struct.pack('iL', bytes, interface_names.buffer_info()[0])
    res = fcntl.ioctl(s.fileno(), SIOCGIFCONF, inbytes)
    returned_bytes = struct.unpack('iL', res)[0]
    interface_names_str = interface_names.tostring()
    intf_list = []
    for i in range(0, returned_bytes, 40):
        intfn = interface_names_str[i:i+16].split('\0', 1)[0]
        intf_list.append(intfn)
    logger.info(intf_list)
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
