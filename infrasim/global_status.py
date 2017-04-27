import os
import re
from texttable import Texttable
from infrasim.config import infrasim_home
from infrasim import run_command
from infrasim import helper


def get_dir_list(p):
    p = str(p)
    if p == "":
        return []
        p = p.replace("\\", "/")
        if p[-1] != "/":
            p += "/"
    a = os.listdir(p)
    b = [x for x in a if os.path.isdir(os.path.join(p, x))]
    return b


def get_task_pid(pid_file):
    try:
        with open(pid_file, "r") as f:
            pid = f.readline().strip()
    except Exception:
        return -1

    if pid == "":
        return -1

    return pid


class NodeStatus(object):
    def __init__(self, node_name):
        self.__node_name = node_name

    def get_node_name(self):
        return self.__node_name

    def get_node_status(self):
        base_path = os.path.join(infrasim_home, self.__node_name)
        task_name = ['socat', 'bmc', 'node', 'racadm', 'ipmi_console']
        task_list = {}
        for task in task_name:
            if task is 'ipmi_console':
                pid_file = os.path.join(base_path, '.ipmi_console.pid')
            else:
                pid_file = os.path.join(base_path, ".{}-{}.pid".format(self.__node_name, task))
            if os.path.exists(pid_file):
                task_pid = get_task_pid(pid_file)
                if not os.path.exists("/proc/{}".format(task_pid)):
                    os.remove(pid_file)
                elif task_pid > 0:
                    task_list[task] = "{:<6}".format(task_pid)
        return task_list

    def get_port_status(self):
        # SSH ~ ipmi-console        default: 9300   tcp
        # ipmi-console ~ ipmi-sim   default: 9000   tcp
        # ipmi-sim ~ qemu           default: 9002   tcp
        # ipmitool ~ ipmi-sim       default: 623    udp
        # telnet client ~ qemu      default: 2345   tcp
        # VNC client ~ qemu         default: 5901   tcp
        # telnet client ~ racadm    default: 10022  tcp
        port_list = []
        task_pid = []
        base_path = os.path.join(infrasim_home, self.__node_name)
        task_name = ['socat', 'bmc', 'node', 'racadm', 'ipmi_console']
        for task in task_name:
            if task is 'ipmi_console':
                pid_file = os.path.join(base_path, '.ipmi_console.pid')
            else:
                pid_file = os.path.join(base_path, ".{}-{}.pid".format(
                    self.__node_name, task))
            if os.path.exists(pid_file):
                pid = get_task_pid(pid_file)
                if pid > 0 and os.path.exists("/proc/{}".format(pid)):
                    task_pid.append(pid)
        for pid in task_pid:
            cmd = "netstat -anp | grep {}".format(pid)

            res = helper.try_func(600, run_command, cmd)
            port = re.findall(r":(\d.+?) ", res[1])
            for p in port:
                if p not in port_list:
                    port_list.append(p)

        return port_list


class InfrasimMonitor(object):

    def __init__(self):
        self.__node_list = []

    def init(self):
        node = get_dir_list(infrasim_home)
        # remove the file whose name starts from "."
        for nd in node:
            if nd[0] is not '.':
                nd_status = NodeStatus(nd)
                self.__node_list.append(nd_status)

    def print_global_status(self):
        socat_flag = False
        racadm_flag = False
        ipmi_console_flag = False
        if not self.__node_list:
            print "There is no node."
            return
        for node in self.__node_list:
            nd_status = node.get_node_status()
            if 'socat' in nd_status:
                socat_flag = True
            if 'racadm' in nd_status:
                racadm_flag = True
            if 'ipmi_console' in nd_status:
                ipmi_console_flag = True
            if racadm_flag and ipmi_console_flag and socat_flag:
                break
        header_line = ['name', 'bmc pid', 'node pid']
        width = [12, 6, 6]
        align = ['c', 'l', 'l']
        if socat_flag:
            header_line.append('socat pid')
            width.append(6)
            align.append('l')
        if racadm_flag:
            header_line.append('racadm pid')
            width.append(6)
            align.append('l')
        if ipmi_console_flag:
            header_line.append('ipmi-console pid')
            width.append(12)
            align.append('l')
        header_line.append('ports')
        port_width = 80 - 14 - 9 - 9 - socat_flag*9 - \
            racadm_flag*9 - ipmi_console_flag*15
        width.append(port_width-1)
        align.append('l')
        rows = []
        rows.append(header_line)
        for node in self.__node_list:
            nd_status = node.get_node_status()
            line = [node.get_node_name()]
            if 'bmc' in nd_status:
                line.append(nd_status['bmc'])
            else:
                line.append('-')
            if 'node' in nd_status:
                line.append(nd_status['node'])
            else:
                line.append('-')
            if socat_flag:
                if 'socat' in nd_status:
                    line.append(nd_status['socat'])
                else:
                    line.append('-')
            if racadm_flag:
                if 'racadm' in nd_status:
                    line.append(nd_status['racadm'])
                else:
                    line.append('-')
            if ipmi_console_flag:
                if 'ipmi_console' in nd_status:
                    line.append(nd_status['ipmi_console'])
                else:
                    line.append('-')
            port = ''
            for p in node.get_port_status():
                port += "{} ".format(p)
            if port == '':
                line.append('-')
            else:
                line.append(port)
            rows.append(line)
        table = Texttable()
        table_type = ~Texttable.BORDER
        table.set_deco(table_type)
        table.set_cols_width(width)
        table.set_cols_align(align)
        table.add_rows(rows)
        print table.draw() + '\n'
