import sys
import time
import argparse
import config
import model
from yaml_loader import YAMLLoader
from init import infrasim_init
from version import version
import helper


def args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault('args', []).insert(0, (args, kwargs))
        return func
    return _decorator


class NodeCommands(object):
    def _get_node(self, config_file=None):
        node_config = config_file or config.infrasim_initial_config
        with open(node_config, "r") as f:
            node_info = YAMLLoader(f).get_data()

        return model.CNode(node_info)

    def _node_preinit(self, node):
        node.init()
        node.precheck()

    @args("-c", "--config-file", action="store", dest="config_file", help="Node configuration file")
    def start(self, config_file=None):
        node = self._get_node(config_file)
        self._node_preinit(node)
        node.start()

        # get IP address
        print "Infrasim service started.\n" \
            "Node {} graphic interface accessible via: \n" \
            "VNC port: 5901 \n" \
            "Either host IP: {} \n" \
            "depending on host in which network VNC viewer is running". \
            format(node.get_node_name(), helper.ip4_addresses())

    @args("-c", "--config-file", action="store", dest="config_file", help="Node configuration file")
    def stop(self, config_file=None):
        node = self._get_node(config_file)
        self._node_preinit(node)
        node.stop()

    @args("-c", "--config-file", action="store", dest="config_file", help="Node configuration file")
    def restart(self, config_file=None):
        self.stop()
        time.sleep(0.5)
        self.start()

    @args("-c", "--config-file", action="store", dest="config_file", help="Node configuration file")
    def status(self, config_file=None):
        node = self._get_node(config_file)
        self._node_preinit(node)
        node.status()

    @args("-c", "--config-file", action="store", dest="config_file", help="Node configuration file")
    def destroy(self, config_file=None):
        node = self._get_node(config_file)
        self._node_preinit(node)
        node.stop()
        node.terminate_workspace()

    @args("-t", "--type", action="store_true", dest="type", help="Query node info")
    def info(self, type=True):
        pass


class ChassisCommands(object):
    @args("-n", "--node-name", action="store", dest="node_name", help="Node name")
    def start(self, node_name=None):
        print node_name

    @args("-n", "--node-name", action="store", dest="node_name", help="Node name")
    def stop(self, node_name=None):
        print node_name

    @args("-n", "--node-name", action="store", dest="node_name", help="Node name")
    def restart(self, node_name=None):
        print node_name

    @args("-n", "--node-name", action="store", dest="node_name", help="Node name")
    def destroy(self, node_name=None):
        print node_name


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
    'chassis': ChassisCommands
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
    init_parser.add_argument("-i", "--infrasim-home", action="store",
                             help="Target infrasim home foler, default $HOME/.infrasim")
    exclusive_group = init_parser.add_mutually_exclusive_group()
    exclusive_group.add_argument("-c", "--config-file", action="store", help="Node configuration file")
    exclusive_group.add_argument("-t", "--type", action="store", default="quanta_d51", help="Node type test for")


    # just for test exclusive_group.add_argument("-t", "--type", action="store", default="quanta_d51",
    # help="Node type test for")
    # just for test exclusive_group.add_argument("-t", "--type", action="store", default="quanta_d51",

    # version command
    version_parser = subparsers.add_parser("version", help="check version of infrasim and dependencies")
    version_parser.set_defaults(version="version")

    args = parser.parse_args(sys.argv[1:])
    if hasattr(args, "init"):
        # Do init
        infrasim_init(args.type, args.skip_installation, args.infrasim_home, args.config_file)
    elif hasattr(args, "version"):
        # Print version
        print version()
    else:
        fn = args.action_fn
        fn_args = get_func_args(fn, args)

        # Handle the command
        fn(*fn_args)
