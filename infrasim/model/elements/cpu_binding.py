'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
# -*- coding: utf-8 -*-

import re
import copy
import multiprocessing
from infrasim import run_command, has_option
from infrasim.model.core.element import CElement


class CCPUBinding(CElement):
    """
        This class is used to bind physical cpus with threads in the task process
    """
    def __init__(self, cpu_binding):
        super(CCPUBinding, self).__init__()
        self.__cpu_binding = cpu_binding
        # internal dict to store information after processed
        self.__cpu_binding_info = copy.deepcopy(self.__cpu_binding)
        self.__bind_cpus = []
        self.__monitor = None
        self.__main_loop = None
        self.__vcpu = None
        self.__vcpu_quantities = None
        # self.__io_thread = None

    def init(self):
        self.__main_loop = self.__cpu_binding.get("main_loop", {})
        self.__vcpu = self.__cpu_binding.get("vcpu", {})
        # self.__io_thread = self.__cpu_binding.get("io_thread", {})

        self.__cpu_binding_info["main_loop"]["cores"] = self.get_cores(self.__main_loop.get("cores"))
        self.__cpu_binding_info["main_loop"]["threads"] = [-1]
        self.__cpu_binding_info["main_loop"]["policy"] = self.__main_loop.get("policy", "mono")

        self.__cpu_binding_info["vcpu"]["cores"] = self.get_cores(self.__vcpu.get("cores"))
        self.__cpu_binding_info["vcpu"]["threads"] = [-1] * self.vcpu_quantities
        self.__cpu_binding_info["vcpu"]["policy"] = self.__vcpu.get("policy", "mono")

        # self.__cpu_binding["io_thread"]["cores"] = self.get_cores(self.__io_thread.get("cores"))

    def precheck(self):
        # precheck according to different policy
        for key, value in self.__cpu_binding_info.items():
            self.precheck_policy(key, value["threads"], value["cores"], value.get("policy"))

        # check bind cpu count not exceeds physical cpu count
        if self.__bind_cpus and len(self.__bind_cpus) >= multiprocessing.cpu_count():
            print("\033[93mWarning:\033[0m Number of cpus trying to bind is larger than"
                  " number of physical cpus, not binding...")
            self.logger.warning("[CCPUBinding] number of bind cpus {} is larger"
                                " than number of physical cpus {}, not binding".
                                format(self.__bind_cpus, multiprocessing.cpu_count()))
            self.__bind_cpus = []

        # check physical cpus are isolated
        fd = open("/sys/devices/system/cpu/isolated", "r")
        rst = fd.read()
        fd.close()
        cpu_list = self.get_cores(rst)
        result = all(elem in cpu_list for elem in self.__bind_cpus)
        if not result:
            print("\033[93mWarning:\033[0m some cpus in bind_cpus are not isolated,"
                  " please check your configuration")
            print("\033[93mbind_cpus:\033[0m {}").format(self.__bind_cpus)
            print("\033[93misolated cpus:\033[0m {}").format(cpu_list)
            self.logger.warning("[CCPUBinding] some cpus in bind_cpus are not isolated,"
                                " please check your configuration")
            self.__bind_cpus = []

        # check binding cpus are in the same socket
        fd = open("/proc/cpuinfo", "r")
        lines = fd.readlines()
        fd.close()
        phy_id = 0
        processor = 0
        found = False
        sockets = {}
        for line in lines:
            if line.strip():
                name, value = line.split(":", 1)
                name = name.strip()
                value = value.strip()
                if name == "physical id":
                    phy_id = value
                if name == "processor":
                    processor = value
            else:
                if phy_id not in sockets:
                    sockets[phy_id] = []
                sockets[phy_id].append(int(processor))
        for value in sockets.itervalues():
            if all(elem in value for elem in self.__bind_cpus):
                found = True
                break
        if not found:
            print("\033[93mWarning:\033[0m bind_cpus are not in the same socket, not binding...")
            self.logger.warning("[CCPUBinding] bind_cpus are not in the same socket, not binding...")
            self.__bind_cpus = []

    def precheck_policy(self, key, threads, cores, policy):
        if policy == "mono":
            if len(threads) != len(cores):
                print("\033[93mWarning:\033[0m Number of binding cpus should be equal to number of threads,"
                      " not binding {}...".format(key))
                self.logger.warning("[CCPUBinding] Number of binding cpus should be equal to number of threads,"
                                    " not binding {}...".format(key))
                del self.__cpu_binding_info[key]
                return
            self.__bind_cpus.extend(cores)
            # check if physical cpus are over used
            dup = sorted(set([x for x in self.__bind_cpus if self.__bind_cpus.count(x) > 1]))
            if dup:
                print("\033[93mWarning:\033[0m Physical cores {} in {} are assigned to multiple threads,"
                      " not align to the policy {}, not binding...".format(dup, key, policy))
                self.logger.warning("[CCPUBinding] Physical cores {} in {} are assigned to multiple threads,"
                                    " not align to the policy {}, not binding...".format(dup, key, policy))
                del self.__cpu_binding_info[key]

        else:
            print("\033[93mWarning:\033[0m Binding policy {} is not supported yet, not binding {}...".format(
                policy, key))
            self.logger.warning("[CCPUBinding] Binding policy {} is not supported yet, not binding {}...".format(
                policy, key))

    def handle_parms(self):
        option = ""
        if self.__bind_cpus:
            option = "-S"
        self.add_option(option)

    @property
    def monitor(self):
        return self.__monitor

    @monitor.setter
    def monitor(self, monitor):
        self.__monitor = monitor

    @property
    def vcpu_quantities(self):
        return self.__vcpu_quantities

    @vcpu_quantities.setter
    def vcpu_quantities(self, vcpu_quantities):
        self.__vcpu_quantities = vcpu_quantities

    def get_cores(self, bind_cpus):
        cores = []
        if not bind_cpus:
            return cores
        cpu_lists = str(bind_cpus).split(",")
        for cpu_list in cpu_lists:
            if cpu_list.find('-') >= 0:
                cpu_range = cpu_list.split('-')
                cores.extend(list(range(int(cpu_range[0]), int(cpu_range[1]) + 1)))
            else:
                cores.append(int(cpu_list))
        return cores

    def get_thread_id(self):
        # get vcpu process id
        vcpu_thread_ids = []
        payload = {
            "execute": "human-monitor-command",
            "arguments": {
                "command-line": "info cpus"
            }
        }
        self.__monitor.open()
        self.__monitor.send(payload)
        res = self.__monitor.recv().get("return")
        self.__monitor.close()
        for s in res.split('\n'):
            vcpu_thread_id = re.search(r"thread_id=(\d+)", s)
            if vcpu_thread_id:
                vcpu_thread_ids.append(vcpu_thread_id.group(1))
        return vcpu_thread_ids

    def bind_cpus_with_policy(self, threads, cores, policy):
        if policy == "mono":
            self.bind_cpus_mono(cores, threads)
        else:
            # TODO: call other binding methods
            pass

    def bind_cpus_mono(self, cores, threads):
        try:
            i = 0
            for core in cores:
                if i < len(cores):
                    cmd = "taskset -pc {} {}".format(core, threads[i])
                    run_command(cmd)
                i = i + 1
        except Exception as e:
            self.logger.warning('[CCPUBinding] {}'.format(str(e)))

    def run_vm(self):
        payload = {
            "execute": "cont",
        }
        self.__monitor.open()
        self.__monitor.send(payload)
        self.__monitor.recv()
        self.__monitor.close()
        self.logger.info("[CCPUBinding] bind physical cpus {} to compute".format(self.__bind_cpus))

    def bind_cpus(self):
        if not self.__bind_cpus:
            return
        if has_option(self.__cpu_binding_info, "main_loop"):
            self.__cpu_binding_info["main_loop"]["threads"] = [self.owner.get_task_pid()]
        if has_option(self.__cpu_binding_info, "vcpu"):
            self.__cpu_binding_info["vcpu"]["threads"] = self.get_thread_id()

        for _, value in self.__cpu_binding_info.items():
            self.bind_cpus_with_policy(value["threads"], value["cores"], value.get("policy"))

        self.run_vm()
