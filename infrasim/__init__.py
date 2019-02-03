import subprocess
import inspect
import pkg_resources
from .log import infrasim_log, LoggerType

logger = infrasim_log.get_logger(LoggerType.cmd.value)

try:
    __version__ = pkg_resources.get_distribution('infrasim-compute').version
except pkg_resources.DistributionNotFound:
    __version__ = None


def run_command(cmd="", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    :param cmd: the command should run
    :param shell: if the type of cmd is string, shell should be set as True, otherwise, False
    :param stdout: reference subprocess module
    :param stderr: reference subprocess module
    :return: tuple (return code, output)
    """
    child = subprocess.Popen(cmd, shell=shell, stdout=stdout, stderr=stderr)
    cmd_result = child.communicate()
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        result = ""
        if cmd_result[1] is not None:
            result = cmd + ":" + cmd_result[1]
        else:
            result = cmd
        logger.error(result)
        raise CommandRunFailed(result, cmd_result[0])
    return 0, cmd_result[0]


def run_command_with_user_input(cmd="", shell=True, stdout=None, stderr=None, stdin=None, interactive_input=""):
    """
    :param cmd: the command should run
    :param shell: if the type of cmd is string, shell should be set as True, otherwise, False
    :param stdout: reference subprocess module
    :param stderr: reference subprocess module
    :param stdin: reference subprocess module
    :return: tuple (return code, output)
    """
    child = subprocess.Popen(cmd, shell=shell,
                             stdout=stdout, stdin=stdin, stderr=stderr)
    cmd_result = child.communicate(interactive_input)
    cmd_return_code = child.returncode
    if cmd_return_code != 0:
        return -1, cmd_result[1]
    return 0, cmd_result[0]


def has_option(config, *args):
    """
    Check if config has these option chains
    :param config: a python dict
    :param args: a list of option chains, e.g.
    if config is:
    {
        "a": {"b": 1}
    }
    has_option(config, "a", "b") returns True
    has_option(config, "b") returns False
    has_option(config, "a", "c") returns False
    """
    if len(args) == 0:
        raise Exception(has_option.__doc__)
    section = config
    for option in args:
        try:
            iter(section)
        except TypeError:
            return False
        if option in section:
            section = section[option]
        else:
            return False
    return True


def set_option(_dict, *args):
    # add dict value by cuple recursively.
    # create key if it is not exist.
    if len(args) < 2:
        raise ArgsNotCorrect("set_option() need at least 1 key:value")
    if len(args) == 2:
        _dict[args[0]] = args[1]
    else:
        k = args[0]
        args = args[1:]
        if k not in _dict or not isinstance(_dict[k], dict):
            _dict[k] = {}
        set_option(_dict[k], *args)


class InfraSimError(Exception):
    def __init__(self, value):
        self.value = value
        logger.exception("{}, stack:\n{}".format(self.value,
                                                 str(inspect.stack()[1:]).replace("), (", "),\n(")))

    def __str__(self):
        return repr(self.value)


class CommandNotFound(InfraSimError):
    pass


class DirectoryNotFound(InfraSimError):
    pass


class CommandRunFailed(InfraSimError):
    def __init__(self, value, output):
        self.value = value
        self.output = output


class ArgsNotCorrect(InfraSimError):
    pass


class NodeAlreadyRunning(InfraSimError):
    pass


class WorkspaceExisting(InfraSimError):
    pass
