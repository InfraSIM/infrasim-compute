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
import socket
import multiprocessing
import types
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
from infrasim import InfraSimError
from . import logger

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
        except OSError, e:
            print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
            sys.exit(1)

        os.setsid()

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                os._exit(os.EX_OK)
        except OSError, e:
            print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
            sys.exit(1)

        try:
            ret = func(*args, **kwargs)
        except Exception, e:
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
    for i in range(times):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            time.sleep(0.5)
            continue
    raise Exception(
        "Tried {} times already, but still failed to run {}".format(
            times, func))

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
            for i in range(1,5):
                if int(p.group(i),0) not in range(0,256):
                    return False
            return True
        else:
            return False
    elif type(ip) is types.ListType:
        if len(ip) != 4:
            return False
        else:
            for i in range(4):
                if type(ip[i]) is not types.IntType:
                    return False
                elif ip[i] not in range(0,256):
                    return False
            return True
    else:
        return False
