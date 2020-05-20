# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

from collections import abc

from . import OPS
from .cmdbase import _CommandBase


def is_op(string):
    return string in OPS


def is_cmdcls(obj):
    """Whether `obj` is a command class"""
    return isinstance(obj, type) and \
        obj is not _CommandBase and \
        issubclass(obj, _CommandBase)


def listify_args(args):
    """
    Make list from `args`

    Ensure `args` is a string and use split(',') to turn it into a list.  If
    `args` is any non-string iterable, recursively listify each item and append
    it to the final list.

    Despite the name, return a tuple.
    """
    if args is None:
        return []

    if isinstance(args, str):
        # args is a string of comma-separated list items
        args = (str(arg).strip() for arg in args.split(','))
    elif isinstance(args, abc.Iterable):
        # args is an iterable of list items; each item may be a string of
        # comma-separated items
        args = (a for arg in args
                for a in listify_args(arg))
    else:
        # args is something else
        args = (str(args).strip())
    return [arg for arg in args if arg]


def log_msgs(process, response, quiet=False):
    """
    Get messages for the user from `response` and report it to the user

    `process` must be an object with `info` and `error` methods (i.e. a command
    instance) that take a single string and report it to the user.

    `response` must be an object with the attributes `msgs` and `errors` (i.e. a
    Reponse instance).

    If `quiet` evaluates to True, only errors are reported.
    """
    if not quiet:
        for msg in response.msgs:
            process.info(msg)

    for error in response.errors:
        process.error(error)
