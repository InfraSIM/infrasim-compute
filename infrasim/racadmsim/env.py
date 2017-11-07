#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import threading


auth_map = {}
racadm_data = None
logger_r = None
node_name = None
#local_env is a thread-safe variable set
local_env = threading.local()

