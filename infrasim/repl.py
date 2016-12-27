#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''

# Refer to Lie Ryan's answer at stackoverflow
# question: "Design python like interactive shell"

from __future__ import print_function
from functools import wraps
from os import linesep
import inspect
import traceback
import sys


class register(object):
    """
    Do nothing, but wrap fn as a callable instance of type "register"
    """
    def __init__(self, fn):
        self.fn = fn

    def __call__(self):
        @wraps(self.fn)
        def wrapper(*args, **kwargs):
            return self.fn(*args, **kwargs)
        return wrapper


def registered(func):
    if isinstance(func, register):
        return True
    else:
        return False


def parse(s):
    """
    Given a command string `s` produce an AST
    """
    # the simplest parser is just splitting the input string,
    # but you can also produce use a more complicated grammer
    # to produce a more complicated syntax tree
    return s.split()


class QuitREPL(Exception):
    pass


class REPL(object):

    def __init__(self):
        self.context = {}
        self.commands = {}
        self.prompt = '> '
        self.input = raw_input
        self.output = print

        # If any method is wrapped as "register", add it into
        # command map
        for m_def in inspect.getmembers(self, predicate=registered):
            m_name = m_def[0]
            m_func = m_def[1]
            self.commands[m_name] = m_func()

    def do(self, cmd):
        """
        Evaluate the AST, producing an output and/or side effect
        """
        # here, we simply use the first item in the list to choose which function to call
        # in more complicated ASTs, the type of the root node can be used to pick actions

        # Handle ENTER with no input
        if not cmd:
            return None

        if cmd[0] not in self.commands:
            self.output('Unknown command, run "help" for detail'+linesep)
            return None

        func = self.commands[cmd[0]]
        try:
            rsp = func(self, self.context, cmd)
            if rsp is None:
                return linesep
            else:
                return str(rsp)+linesep
        except QuitREPL:
            raise
        except Exception:
            return traceback.format_exc()+linesep

    def run(self):
        self.welcome()
        while True:
            # READ
            inp = self.input(self.prompt)

            # EVAL
            cmd = parse(inp)
            try:
                out = self.do(cmd)
            except EOFError:
                return
            except QuitREPL:
                return

            # PRINT
            if out is not None:
                self.output(out)

    def welcome(self):
        self.output("Welcome to {}{}".
                    format(self.__class__.__name__, linesep))

    def set_prompt(self, prompt="> "):
        self.prompt = prompt

    def set_input(self, input=sys.stdin):
        self.input = input

    def set_output(self, output=sys.stdout):
        self.output = output

    @register
    def assign(self, ctx, args):
        """
        Assign values
            assign [a] [b]
        Create a variable a in context and assign it with value b
        """
        ctx[args[1]] = args[2]
        return '%s = %s' % (args[1], args[2])

    @register
    def printvar(self, ctx, args):
        """
        Print a variable's value in context
        """
        return ctx[args[1]]

    @register
    def define(self, ctx, args):
        """
        Define a quick function
        """
        body = ' '.join(args[2:])
        ctx[args[1]] = compile(body, '', 'exec')
        return 'def %s(): %s' % (args[1], body)

    @register
    def call(self, ctx, args):
        """
        Call the function you define
        """
        exec ctx[args[1]] in ctx
        return None

    @register
    def exit(self, ctx, args):
        """
        Exit this console
        """
        self.output("Exit {} console, good bye!{}".
                    format(self.__class__.__name__, linesep))
        raise QuitREPL()

    @register
    def quit(self, ctx, args):
        """
        Quit this console
        """
        self.output("Quit {} console, good bye!{}".
                    format(self.__class__.__name__, linesep))
        raise QuitREPL()

    @register
    def help(self, ctx, args):
        """
        Show command helps
        """

        if len(args) >= 2:
            fn_list = args[1:]
        else:
            fn_list = self.commands

        lines = []

        for fn in sorted(fn_list):
            func = self.commands[fn]
            try:
                simple_doc = func.__doc__.splitlines()[1]
            except IndexError:
                simple_doc = ""
            except AttributeError:
                simple_doc = ""
            lines.append("\t{:<12}{}".format(fn, simple_doc))

        return linesep.join(lines)

if __name__ == "__main__":
    repl = REPL()
    repl.run()
