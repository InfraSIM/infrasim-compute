'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import netifaces
import socket


def check_kvm_existence():
    if os.path.exists("/dev/kvm"):
        return True
    return False


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
