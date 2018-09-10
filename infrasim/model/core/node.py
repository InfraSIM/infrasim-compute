'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import os
import shutil
import uuid
import time

from infrasim import ArgsNotCorrect
from infrasim import config, helper
from infrasim.helper import run_in_namespace
from infrasim.log import infrasim_log, LoggerType
from infrasim.model.tasks.bmc import CBMC
from infrasim.model.tasks.compute import CCompute
from infrasim.model.tasks.monitor import CMonitor
from infrasim.model.tasks.racadm import CRacadm
from infrasim.model.tasks.socat import CSocat
from infrasim.workspace import Workspace


class CNode(object):

    def __init__(self, node_info=None):
        self.__tasks_list = []
        self.__node = node_info
        self.__node_name = ""
        self.workspace = None
        self.__sol_enabled = None
        self.__netns = None
        self.__logger = infrasim_log.get_logger(LoggerType.model.value)
        self.__shm_key = None

    @property
    def netns(self):
        return self.__netns

    def get_task_list(self):
        return self.__tasks_list

    def get_node_name(self):
        return self.__node_name

    def set_node_name(self, name):
        self.__node_name = name

    def get_node_info(self):
        return self.__node

    @run_in_namespace
    def precheck(self):
        if self.__is_running():
            return

        for task in self.__tasks_list:
            task.precheck()

    def terminate_workspace(self):
        if Workspace.check_workspace_exists(self.__node_name):
            shutil.rmtree(self.workspace.get_workspace())
        self.__logger.info("[Node] Node {} runtime workspcace is destroyed".
                           format(self.__node_name))
        print "Node {} runtime workspace is destroyed.".format(self.__node_name)

    def init(self):
        """
        1. Prepare CNode attributes:
            - self.__node
        2. Then use this information to init workspace
        3. Use this information to init sub module
        """
        if 'name' in self.__node:
            self.set_node_name(self.__node['name'])
        else:
            raise ArgsNotCorrect("[Node] No node name is given in node information.")

        self.__logger = infrasim_log.get_logger(LoggerType.model.value,
                                                self.__node_name)

        if self.__node['compute'] is None:
            raise ArgsNotCorrect("[Node] No compute information")

        if 'sol_enable' not in self.__node:
            self.__node['sol_enable'] = True
        self.__sol_enabled = self.__node['sol_enable']

        self.__netns = self.__node.get("namespace")

        # If user specify "network_mode" as "bridge" but without MAC
        # address, generate one for this network.
        for network in self.__node['compute']['networks']:
            if 'mac' not in network:
                uuid_val = uuid.uuid4()
                str1 = str(uuid_val)[-2:]
                str2 = str(uuid_val)[-4:-2]
                str3 = str(uuid_val)[-6:-4]
                network['mac'] = ":".join(["52:54:BE", str1, str2, str3])

        # If user specify "nmve" controller(drive) in "storage_backend"
        # with NO serial, generate one for it, since QEMU now (2.10.1)
        # treat "serail" as a mandatory attribute for "nvme"
        for storage in self.__node['compute']['storage_backend']:
            if storage.get('type') == 'nvme':
                if not storage.get('serial', ''):
                    storage['serial'] = helper.random_serial()

        if self.__sol_enabled:
            socat_obj = CSocat()
            socat_obj.logger = self.__logger
            socat_obj.set_priority(0)
            socat_obj.set_task_name("{}-socat".format(self.__node_name))
            socat_obj.set_node_name(self.__node['name'])
            self.__tasks_list.append(socat_obj)

        bmc_info = self.__node.get('bmc', {})
        bmc_obj = CBMC(bmc_info)
        bmc_obj.logger = self.__logger
        bmc_obj.set_priority(1)
        bmc_obj.set_task_name("{}-bmc".format(self.__node_name))
        bmc_obj.enable_sol(self.__sol_enabled)
        bmc_obj.set_log_path(os.path.join(config.infrasim_log_dir, self.__node_name, "openipmi.log"))
        bmc_obj.set_node_name(self.__node['name'])
        self.__tasks_list.append(bmc_obj)

        compute_obj = CCompute(self.__node['compute'])
        compute_obj.logger = self.__logger
        asyncr = bmc_info.get("startnow", True)
        compute_obj.set_asyncronous(asyncr)
        compute_obj.enable_sol(self.__sol_enabled)
        compute_obj.set_priority(2)
        compute_obj.set_task_name("{}-node".format(self.__node_name))
        compute_obj.set_log_path(os.path.join(config.infrasim_log_dir, self.__node_name, "qemu.log"))
        self.__tasks_list.append(compute_obj)

        if "type" in self.__node and "dell" in self.__node["type"]:
            racadm_info = self.__node.get("racadm", {})
            racadm_obj = CRacadm(racadm_info)
            racadm_obj.logger = self.__logger
            racadm_obj.set_priority(3)
            racadm_obj.set_node_name(self.__node_name)
            racadm_obj.set_task_name("{}-racadm".format(self.__node_name))
            racadm_obj.set_log_path(os.path.join(config.infrasim_log_dir, self.__node_name, "racadm.log"))
            self.__tasks_list.append(racadm_obj)

        # Set interface
        if "type" not in self.__node:
            raise ArgsNotCorrect("[Node] Can't get infrasim type")
        else:
            bmc_obj.set_type(self.__node['type'])
            compute_obj.set_type(self.__node['type'])

        if self.__sol_enabled:
            if "sol_device" in self.__node:
                socat_obj.set_sol_device(self.__node["sol_device"])
                bmc_obj.set_sol_device(self.__node["sol_device"])

            if "serial_socket" not in self.__node:
                self.__node["serial_socket"] = os.path.join(config.infrasim_home,
                                                            self.__node["name"],
                                                            ".serial")
            socat_obj.set_socket_serial(self.__node["serial_socket"])
            compute_obj.set_socket_serial(self.__node["serial_socket"])

        if "ipmi_console_port" in self.__node:
            bmc_obj.set_port_ipmi_console(self.__node["ipmi_console_port"])
            # ipmi-console shall connect to same port with the same conf file

        if "bmc_connection_port" in self.__node:
            bmc_obj.set_port_qemu_ipmi(self.__node["bmc_connection_port"])
            compute_obj.set_port_qemu_ipmi(self.__node["bmc_connection_port"])

        # Init monitor task
        monitor_info = {}
        if "monitor" not in self.__node:
            monitor_info = {
                "enable": True,
                # Interface and port is for north bound REST service of
                # infrasim-monitor, not the socket of QEMU monitor
                "inferface": None,
                "port": 9005
            }
        else:
            monitor_info = {
                "enable": self.__node["monitor"].get("enable", True),
                "interface": self.__node["monitor"].get("interface", None),
                "port": self.__node["monitor"].get("port", 9005)
            }
        if not isinstance(monitor_info["enable"], bool):
            raise ArgsNotCorrect("[Monitor] Invalid setting")
        if monitor_info["enable"]:
            compute_obj.enable_qemu_monitor()
            monitor_obj = CMonitor(monitor_info)
            monitor_obj.logger = self.__logger
            monitor_obj.set_priority(4)
            monitor_obj.set_node_name(self.__node_name)
            monitor_obj.set_task_name("{}-monitor".format(self.__node_name))
            monitor_obj.set_log_path(os.path.join(config.infrasim_log_dir, self.__node_name, "monitor.log"))
            self.__tasks_list.append(monitor_obj)

        self.workspace = Workspace(self.__node)

        for task in self.__tasks_list:
            task.set_workspace(self.workspace.get_workspace())

        if not self.__is_running():
            self.workspace.init()

        if self.__netns:
            for task in self.__tasks_list:
                task.netns = self.__netns

        for task in self.__tasks_list:
            task.init()

    # Run tasks list as the priority
    def start(self):
        # sort the tasks as the priority
        self.__tasks_list.sort(key=lambda x: x.get_priority(), reverse=False)

        for task in self.__tasks_list:
            task.run()

    def stop(self):
        # sort the tasks as the priority in reversed sequence
        self.__tasks_list.sort(key=lambda x: x.get_priority(), reverse=True)

        for task in self.__tasks_list:
            task.terminate()

    def status(self):
        for task in self.__tasks_list:
            task.status()

    def __is_running(self):
        state = True
        for task in self.__tasks_list:
            state &= task.task_is_running()

        return state

    def wait_node_up(self, timeout=180):
        start = time.time()
        while self.__is_running() is False:
            if time.time() - start > timeout:
                return False
        return True
