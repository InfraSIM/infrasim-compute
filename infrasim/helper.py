'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import netifaces
import socket
from functools import wraps
import sys
from ctypes import cdll

libc = cdll.LoadLibrary('libc.so.6')
setns = libc.setns


def check_kvm_existence():
    if os.path.exists("/dev/kvm"):
        return True
    return False


def run_in_namespace(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        namespace = sys.modules['__builtin__'].__dict__.get("netns")
        if namespace:
            with Namespace(nsname=namespace):
                ret = func(*args, **kwargs)
        else:
            ret = func(*args, **kwargs)
        return ret
    return wrapper


@run_in_namespace
def get_interface_ip(interface):
    """
    Get IP address given a interface name
    :param interface: interface name
    :return: empty string if no such interface, else IP address
    """
    try:
        addr = netifaces.ifaddresses(interface)
    except ValueError:
        return ""

    try:
        ip = addr[netifaces.AF_INET][0]["addr"]
    except KeyError:
        return ""

    return ip


@run_in_namespace
def ip4_addresses():
    ip_list = []
    for interface in netifaces.interfaces():
        for link in netifaces.ifaddresses(interface).get(netifaces.AF_INET, ()):
            ip_list.append(link['addr'])
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

        if not self.targetpath:
            raise ValueError('invalid namespace')

    def __enter__(self):
        self.myns = open(self.mypath)
        with open(self.targetpath) as fd:
            setns(fd.fileno(), 0)

    def __exit__(self, *args):
        setns(self.myns.fileno(), 0)
        self.myns.close()
