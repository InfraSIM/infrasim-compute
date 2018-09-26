import argparse
from functools import wraps
import inspect
import os
import sys
import time
from texttable import Texttable

from global_status import InfrasimMonitor
from infrasim import InfraSimError
from infrasim.config_manager import NodeMap, ChassisMap
import infrasim.helper as helper
from infrasim.init import infrasim_init
import infrasim.model as model
from infrasim.version import version
from infrasim.workspace import Workspace, ChassisWorkspace
from infrasim.yaml_loader import YAMLLoader

from .log import LoggerType, infrasim_log

nm = NodeMap()
logger_cmd = infrasim_log.get_logger(LoggerType.cmd.value)
cm = ChassisMap(nm)


def args(*args, **kwargs):

    def _decorator(func):
        func.__dict__.setdefault('args', []).insert(0, (args, kwargs))
        return func

    return _decorator


def node_workspace_exists(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        frame = inspect.currentframe()
        frame_args, _, _, values = inspect.getargvalues(frame)
        node_name = values["args"][1]
        if not Workspace.check_workspace_exists(node_name):
            print "Node {} runtime workspace doesn't exist".format(node_name)
            logger_cmd.warning("cmd res: Node {} runtime workspace doesn't exist".format(node_name))
            return
        return func(*args, **kwargs)

    return wrapper


class ConfigCommands(object):

    def _get_map_manager(self, name, config_file=None):
        is_chassis = False
        has_node = nm.in_map_folder(name)
        has_chassis = cm.in_map_folder(name)

        if config_file:
            with open(config_file, 'r') as fp:
                info = YAMLLoader(fp).get_data()
            if info.get("nodes"):
                is_chassis = True

            if (is_chassis and has_node) or (is_chassis is False and has_chassis):
                raise InfraSimError("Type from config file is not match with name")
        else:
            is_chassis = has_chassis

        return cm if is_chassis else nm

    @args("name", help="Specify name to add configuration mapping")
    @args("config_file", help="Node Config File Path")
    def add(self, name, config_file):
        try:
            mm = self._get_map_manager(name, config_file)
            mm.add(name, config_file)
            logger_cmd.info("cmd res: add {} OK".format(name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    @args("name", help="Specify name to delete configuration mapping")
    def delete(self, name):
        try:
            mm = self._get_map_manager(name)
            mm.delete(name)
            logger_cmd.info("cmd res: delete {} OK".format(name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    @args("name", help="Specify name to update configuration mapping")
    @args("config_file", help="Node Config File Path")
    def update(self, name, config_file):
        try:
            mm = self._get_map_manager(name, config_file)
            mm.update(name, config_file)
            logger_cmd.info("cmd res: update {} OK".format(name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

        if Workspace.check_workspace_exists(name):
            print "{1} {0} runtime workspace exists.\n" \
                  "If you want to apply updated configuration, please destroy runtime workspace first.\n" \
                  "You can run commands: \n" \
                  "    infrasim {1} destroy {0}\n" \
                  "    infrasim {1} start {0}".format(name, mm.get_type())
            logger_cmd.warning("{1} {0} runtime workspace exists. "
                               "Need to destroy {1} runtime workspace first".format(name, mm.get_type()))

    @args("name", nargs='?', default="default",
          help="Specify name to open its configuration in editor")
    def edit(self, name):
        mm = self._get_map_manager(name)
        if name not in mm.get_name_list():
            print "Fail to find {0} configuration. It is not registered. Check by:\n" \
                  "    infrasim config list".format(name)
            logger_cmd.warning("cmd res: Fail to find {0} configuration. It is not registered. Check by:\n"
                               "    infrasim config list".format(name))
            return

        editor = os.environ.get('EDITOR', 'vi')
        config_path = os.path.join(mm.get_mapping_folder(),
                                   "{}.yml".format(name))
        try:
            os.system("{} {}".format(editor, config_path))
            if Workspace.check_workspace_exists(name):
                print "Warning: " \
                      "\033[93mPlease destroy {}\033[0m " \
                      "before start or restart, " \
                      "or this edit won't work." .format(name)
            logger_cmd.info("cmd res: edit {} OK".format(name))
        except OSError as e:
            print e
            logger_cmd.error("cmd res: {}".format(e))

    def list(self):
        try:
            print "\033[1;93;44mChassis list\033[0m"
            cm.list()
            print "\n\033[1;93;44mNode list\033[0m"
            nm.list()
            logger_cmd.info("cmd res: list OK")
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))


class NodeConfigCommands(object):

    def add(self, node_name, config_file):
        try:
            nm.add(node_name, config_file)
            logger_cmd.info("cmd res: add node {} OK".format(node_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    def delete(self, node_name):
        try:
            nm.delete(node_name)
            logger_cmd.info("cmd res: delete node {} OK".format(node_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    def update(self, node_name, config_file):
        try:
            nm.update(node_name, config_file)
            logger_cmd.info("cmd res: update node {} OK".format(node_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

        if Workspace.check_workspace_exists(node_name):
            print "Node {0} runtime workspace exists.\n" \
                  "If you want to apply updated configuration, please destroy node runtime workspace first.\n" \
                  "You can run commands: \n" \
                  "    infrasim node destroy {0}\n" \
                  "    infrasim node start {0}".format(node_name)
            logger_cmd.warning("Node {0} runtime workspace exists. "
                               "Need to destroy node runtime workspace first".format(node_name))

    def edit(self, node_name):
        if node_name not in nm.get_name_list():
            print "Fail to find node {0} configuration. It is not registered. Check by:\n" \
                  "    infrasim config list".format(node_name)
            logger_cmd.warning("cmd res: Fail to find node {0} configuration. It is not registered. Check by:\n"
                               "    infrasim config list".format(node_name))
            return

        editor = os.environ.get('EDITOR', 'vi')
        config_path = os.path.join(nm.get_mapping_folder(),
                                   "{}.yml".format(node_name))
        try:
            os.system("{} {}".format(editor, config_path))
            if Workspace.check_workspace_exists(node_name):
                print "Warning: " \
                      "\033[93mPlease destroy node {}\033[0m " \
                      "before start or restart, " \
                      "or this edit won't work." .format(node_name)
            logger_cmd.info("cmd res: edit node {} OK".format(node_name))
        except OSError as e:
            print e
            logger_cmd.error("cmd res: {}".format(e))

    def list(self):
        try:
            nm.list()
            logger_cmd.info("cmd res: list OK")
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))


class ChassisConfigCommands(object):

    def add(self, chassis_name, config_file):
        try:
            cm.add(chassis_name, config_file)
            logger_cmd.info("cmd res: add chassis {} OK".format(chassis_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    def delete(self, chassis_name):
        try:
            cm.delete(chassis_name)
            logger_cmd.info("cmd res: delete chassis {} OK".format(chassis_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    def update(self, chassis_name, config_file):
        try:
            cm.update(chassis_name, config_file)
            logger_cmd.info("cmd res: update chassis {} OK".format(chassis_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

        if Workspace.check_workspace_exists(chassis_name):
            print "chassis {0} runtime workspace exists.\n" \
                  "If you want to apply updated configuration, please destroy chassis runtime workspace first.\n" \
                  "You can run commands: \n" \
                  "    infrasim chassis destroy {0}\n" \
                  "    infrasim chassis start {0}".format(chassis_name)
            logger_cmd.warning("chassis {0} runtime workspace exists. "
                               "Need to destroy chassis runtime workspace first".format(chassis_name))

    def edit(self, chassis_name):
        if chassis_name not in cm.get_name_list():
            print "Fail to find chassis {0} configuration. It is not registered. Check by:\n" \
                  "    infrasim config list".format(chassis_name)
            logger_cmd.warning("cmd res: Fail to find chassis {0} configuration. It is not registered. Check by:\n"
                               "    infrasim config list".format(chassis_name))
            return

        editor = os.environ.get('EDITOR', 'vi')
        config_path = os.path.join(cm.get_mapping_folder(),
                                   "{}.yml".format(chassis_name))
        try:
            os.system("{} {}".format(editor, config_path))
            if Workspace.check_workspace_exists(chassis_name):
                print "Warning: " \
                      "\033[93mPlease destroy chassis {}\033[0m " \
                      "before start or restart, " \
                      "or this edit won't work." .format(chassis_name)
            logger_cmd.info("cmd res: edit chassis {} OK".format(chassis_name))
        except OSError as e:
            print e
            logger_cmd.error("cmd res: {}".format(e))

    def list(self):
        try:
            cm.list()
            logger_cmd.info("cmd res: list OK")
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))


class NodeCommands(object):

    def _node_preinit(self, node, ignore_check=False):
        node.init()

        if ignore_check:
            return

        node.precheck()

    @args("node_name", nargs='?', default="default", help="Specify node name to start")
    def start(self, node_name):
        try:
            if Workspace.check_workspace_exists(node_name):
                node_info = Workspace.get_node_info_in_workspace(node_name)
            else:
                node_info = nm.get_item_info(node_name)
            node = model.CNode(node_info)
            self._node_preinit(node)

        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))
            return

        node.start()

        vnc_port = node_info["compute"].get("vnc_display", 1) + 5900

        # get IP address
        print "Infrasim service started.\n" \
            "Node {} graphic interface accessible via: \n" \
            "VNC port: {} \n" \
            "Either host IP: {} \n" \
            "depending on host in which network VNC viewer is running \n"\
            "Node log folder: {}". \
            format(node.get_node_name(),
                   vnc_port,
                   helper.ip4_addresses(netns=node_info.get("namespace")),
                   infrasim_log.get_log_path(node_name))
        logger_cmd.info("cmd res: start node {} OK".format(node_name))

    @node_workspace_exists
    @args("node_name", nargs='?', default="default", help="Specify node name to stop")
    def stop(self, node_name):
        try:
            node_info = Workspace.get_node_info_in_workspace(node_name)
            node = model.CNode(node_info)
            self._node_preinit(node, ignore_check=True)
            node.stop()
            logger_cmd.info("cmd res: stop node {} OK".format(node_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))
            return

    @node_workspace_exists
    @args("node_name", nargs='?', default="default", help="Specify node name to restart")
    def restart(self, node_name):
        self.stop(node_name)
        time.sleep(0.5)
        self.start(node_name)
        logger_cmd.info("cmd res: restart node {} OK".format(node_name))

    @node_workspace_exists
    @args("node_name", nargs='?', default="default", help="Specify node name to check status")
    def status(self, node_name):
        try:
            node_info = Workspace.get_node_info_in_workspace(node_name)
            node = model.CNode(node_info)
            self._node_preinit(node, ignore_check=True)
            node.status()
            logger_cmd.info("cmd res: get node {} status OK".format(node_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))

    @args("node_name", nargs='?', default="default", help="Specify node name to destroy")
    def destroy(self, node_name):
        if Workspace.check_workspace_exists(node_name):
            try:
                node_info = Workspace.get_node_info_in_workspace(node_name)
            except InfraSimError as e:
                print e.value
                logger_cmd.error("cmd res: {}".format(e.value))
                return
        else:
            print "Node {} runtime workspace is not found, destroy action is not applied.".\
                format(node_name)
            logger_cmd.warning("cmd res: Node {} runtime workspace is not found, "
                               "destroy action is not applied.".format(node_name))
            return
        node = model.CNode(node_info)
        try:
            self._node_preinit(node, ignore_check=True)
        except InfraSimError as e:
            print(e.value)
            logger_cmd.error("cmd res: {}".format(e.value))
        except Exception as e:
            print(e)
            logger_cmd.error("cmd res: {}".format(e))
        try:
            node.stop()
            node.terminate_workspace()
            logger_cmd.info("cmd res: destroy node {} OK".format(node_name))
        except Exception as e:
            print("You have to destroy node {} manually due to fatal error: {}".format(node_name, e))

    @node_workspace_exists
    @args("node_name", nargs='?', default="default", help="Specify node name to get information")
    def info(self, node_name, type=True):
        try:
            node_info = Workspace.get_node_info_in_workspace(node_name)
            node_info_net = node_info['compute']['networks']
            node_info_stor = node_info['compute']['storage_backend']
            print "{:<20}{}\n" \
                  "{:<20}{}\n" \
                  "{:<20}{}\n" \
                  "{:<20}{}\n" \
                  "{:<20}{}\n" \
                  "{:<20}{}" . \
                format("node name:", node_name,
                       "type:", node_info['type'],
                       "memory size:", node_info['compute']['memory']['size'],
                       "sol_enable:", node_info['sol_enable'],
                       "cpu quantities:", node_info['compute']['cpu']['quantities'],
                       "cpu type:", node_info['compute']['cpu']['type'])
            print "{:<20}".format("network(s):") + "-" * 22
            table = Texttable()
            table_type = ~(Texttable.HEADER | Texttable.BORDER | Texttable.HLINES | Texttable.VLINES)
            table.set_deco(table_type)
            table.set_cols_align(["l", "l", "l", "l"])
            row = []
            row.append([" " * 17, "device", "mode", "name"])
            for i in range(1, len(node_info_net) + 1):
                net = node_info_net[i - 1]
                row.append([" " * 17, net['device'], net['network_mode'], net['network_name']])
            table.add_rows(row)
            print table.draw()

            print "{:<20}".format("storage backend:") + "-" * 30
            table = Texttable()
            table.set_deco(table_type)
            table.set_cols_align(["l", "l", "l", "l"])
            row = []
            row.append([" " * 17, "type", "max drive", "drive size"])
            for i in range(1, len(node_info_stor) + 1):
                stor = node_info_stor[i - 1]
                if 'drives' in stor.keys():
                    node_info_drives = stor['drives']
                    for j in range(1, len(node_info_drives) + 1):
                        drive = node_info_drives[j - 1]
                        if j % stor['max_drive_per_controller'] == 1:
                            row.append([" " * 17, stor['type'],
                                        stor['max_drive_per_controller'], drive['size']])
                        else:
                            row.append([" " * 17, "", "", drive['size']])
                if 'connectors' in stor.keys():
                    node_info_connectors = stor['connectors']
                    for j in range(1, len(node_info_connectors) + 1):
                        if j % stor['max_drive_per_controller'] == 1:
                            row.append([" " * 17, stor['type'],
                                        stor['max_drive_per_controller'], ""])
                if 'disk_array' in stor.keys():
                    node_info_disk_array = stor['disk_array']
                    for j in range(1, len(node_info_disk_array) + 1):
                        row.append([" " * 17, stor['type'], "", ""])
            table.add_rows(row)
            print table.draw()
            logger_cmd.info("cmd res: get node {} info OK".format(node_name))
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))
            return


class ChassisCommands(object):

    @args("chassis_name", nargs='?', help="Chassis name")
    def start(self, chassis_name=None):
        try:
            if ChassisWorkspace.check_workspace_exists(chassis_name):
                chassis_info = ChassisWorkspace.get_chassis_info_in_workspace(chassis_name)
            else:
                chassis_info = cm.get_item_info(chassis_name)

            chassis = model.CChassis(chassis_name, chassis_info)
            chassis.precheck()
            chassis.init()

        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))
            return

        chassis.start()

        # get IP address
        print "Chassis service for {} started".format(chassis_name)
        logger_cmd.info("cmd res: start node {} chassis OK".format(chassis_name))

    @args("chassis_name", nargs='?', help="Chassis name")
    def stop(self, chassis_name=None):
        try:
            if ChassisWorkspace.check_workspace_exists(chassis_name):
                chassis_info = ChassisWorkspace.get_chassis_info_in_workspace(chassis_name)
            else:
                chassis_info = cm.get_item_info(chassis_name)
            chassis = model.CChassis(chassis_name, chassis_info)
            chassis.init()

        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))
            return
        chassis.stop()
        logger_cmd.info("cmd res: stop node {} chassis OK".format(chassis_name))

    @args("chassis_name", nargs='?', help="Chassis name")
    def restart(self, chassis_name=None):
        self.stop(chassis_name)
        self.start(chassis_name)
        logger_cmd.info("cmd res: restart node {} chassis OK".format(chassis_name))

    @args("chassis_name", nargs='?', help="Chassis name")
    def destroy(self, chassis_name=None):
        if Workspace.check_workspace_exists(chassis_name):
            try:
                chassis_info = ChassisWorkspace.get_chassis_info_in_workspace(chassis_name)
            except InfraSimError as e:
                print e.value
                logger_cmd.error("cmd res: {}".format(e.value))
                return
        else:
            print "Chassis {} runtime workspace is not found, destroy action is not applied.".\
                format(chassis_name)
            logger_cmd.warning("cmd res: Chassis {} runtime workspace is not found, "
                               "destroy action is not applied.".format(chassis_name))
            return
        chassis = model.CChassis(chassis_name, chassis_info)
        try:
            chassis.init()
            chassis.destroy()
        except InfraSimError as e:
            print e.value
            logger_cmd.error("cmd res: {}".format(e.value))
        logger_cmd.info("cmd res: destroy chassis {} OK".format(chassis_name))


class InfrasimCommands(object):

    def status(self):
        monitor = InfrasimMonitor()
        monitor.init()
        monitor.print_global_status()
        logger_cmd.info("cmd res: get global status OK")


def methods_of(obj):
    result = []
    for i in dir(obj):
        if callable(getattr(obj, i)) and not i.startswith('_'):
            result.append((i, getattr(obj, i)))
    return result


def get_arg_string(args):
    args = args.strip('-')

    if args:
        args = args.replace('-', '_')

    return args


def get_func_args(func, matchargs):
    fn_args = []
    for args, kwargs in getattr(func, 'args', []):
        # The for loop is for supporting short and long options
        for arg in args:
            try:
                arg = kwargs.get('dest') or get_arg_string(args[0])
                parm = getattr(matchargs, arg)
            except AttributeError:
                continue

            fn_args.append(parm)

            # If we already got one params for fn, then exit loop.
            if len(fn_args) > 0:
                break

    return fn_args


CATEGORIES = {
    'node': NodeCommands,
    'chassis': ChassisCommands,
    'config': ConfigCommands,
    'global': InfrasimCommands,
}


def add_command_parsers(subparser):
    for category in CATEGORIES:
        command_object = CATEGORIES[category]()

        parser = subparser.add_parser(category)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest="action")

        for (action, action_fn) in methods_of(command_object):
            parser = category_subparsers.add_parser(action)

            action_kwargs = []
            for args, kwargs in getattr(action_fn, 'args', []):
                parser.add_argument(*args, **kwargs)
                parser.set_defaults(dest="dest")

            parser.set_defaults(action_fn=action_fn)
            parser.set_defaults(action_kwargs=action_kwargs)


def command_handler():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(title="InfraSIM Commands:")
    add_command_parsers(subparsers)

    # for init command
    init_parser = subparsers.add_parser("init", help="init infrasim environment")
    init_parser.set_defaults(init="init")
    init_parser.add_argument("-s", "--skip-installation", action="store_true",
                             help="Ignore qemu/openipmi package installation")
    init_parser.add_argument("-f", "--force", action="store_true",
                             help="Destroy existing Nodes")
    init_parser.add_argument("-e", "--entry", action="store",
                             help="source list entry, e.g., "
                             "deb http://download.virtualbox.org/virtualbox/debian trusty contrib")
    exclusive_group = init_parser.add_mutually_exclusive_group()
    exclusive_group.add_argument("-c", "--config-file", action="store", help="Node configuration file")
    exclusive_group.add_argument("-t", "--type", action="store", default="dell_r730", help="Node type")

    # version command
    version_parser = subparsers.add_parser("version", help="check version of infrasim and dependencies")
    version_parser.set_defaults(version="version")

    args = parser.parse_args(sys.argv[1:])
    cmd = ''
    for word in sys.argv[1:]:
        cmd += word + " "
    logger_cmd.info("cmd rev: infrasim {}".format(cmd))
    if hasattr(args, "init"):
        # Do init
        try:
            infrasim_init(args.type, skip_installation=args.skip_installation,
                          force=args.force, config_file=args.config_file, entry=args.entry)
        except Exception as e:
            msg = "Infrasim init failed\nException Type: {}\n" \
                  "Error Message:\n{}".format(e.__class__.__name__,
                                              eval(str(e)))
            logger_cmd.error("cmd res: {} \n".format(msg))
            sys.exit(msg)

    elif hasattr(args, "version"):
        # Print version
        print version()
        logger_cmd.info("cmd res: print version Ok")
    else:
        fn = args.action_fn

        fn_args = get_func_args(fn, args)

        # Handle the command
        fn(*fn_args)
