'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import os


def check_kvm_existence():
    if os.path.exists("/dev/kvm"):
        return True
    return False
