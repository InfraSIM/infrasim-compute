'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-
import threading


PORT_TELNET_TO_VBMC = 9000
PORT_SSH_FOR_CLIENT = 9300
VBMC_IP = "localhost"
VBMC_PORT = 623


# local_env is a thread-safe variable set
local_env = threading.local()

