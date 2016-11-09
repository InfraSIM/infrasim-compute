'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os
import netifaces


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
