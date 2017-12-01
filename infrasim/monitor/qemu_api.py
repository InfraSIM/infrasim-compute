"""
Provide QEMU monitor access interface.
"""

import json
import socket
import time
import os
import threading
from functools import wraps
from infrasim import config
from infrasim.helper import UnixSocket
from infrasim.config import infrasim_home

qm_map = {}

def get_qemu_monitor(node_name):
    if node_name in qm_map:
        return qm_map[node_name]
    else:
        qm_map[node_name] = QemuMonitor(node_name)
        #qm_map[node_name].acquire()
        try:
            qm_map[node_name].connect()
        except IOError:
            del qm_map[node_name]
            return None
        qm_map[node_name].release()

        return qm_map[node_name]

class QemuMonitor(object):

    def __init__(self, node_name):
        self.s = None
        self.node_name = node_name
    
        self.lock_socket = threading.Lock()

        # could be:
        # - hmp, hmp-command
        # - qmp, qmp-command 
        self.cmd_mode = None

    def connect(self):
        path = os.path.join(config.infrasim_home,self.node_name, ".monitor")
        # connect socket
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.connect(path)
        data = ""
        data = self.recv()
        
        payload_enable_qmp = {
            "execute": "qmp_capabilities"
        }
        self.send(payload_enable_qmp)
        data = self.recv()

    def close(self):
        if self.s:
            self.s.close()
            self.s = None

    def send(self, req):
        self.s.send(json.dumps(req))

    def recv(self):
        data = ""
        while 1:
            snip = self.s.recv(1024)
            data += snip
            if len(snip) == 1024:
                continue
            else:
                break
        return data

    def acquire(self, blocking=True):
        return self.lock_socket.acquire(blocking)

    def locked(self):
        return self.lock_socket.locked()

    def release(self):
        return self.lock_socket.release()

