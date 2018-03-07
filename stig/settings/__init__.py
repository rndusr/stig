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

from ..logging import make_logger
log = make_logger(__name__)

from .defaults import init_defaults

from blinker import Signal
from collections import abc


class Settings(abc.Mapping):
    """Specialized mapping for *Value instances"""

    def __init__(self):
        self._defaults = {}
        self._values = {}
        self._constructors = {}
        self._descriptions = {}
        self._signals = {}
        self._global_signal = Signal()

    def add(self, name, constructor, default, description=None):
        """
        Add new setting

        name:        Identifier for this setting
        constructor: Callable that takes one argument and returns a new value
                     for this setting
        default:     Initial and default value
        description: What the setting does
        """
        self._constructors[name] = constructor
        self._signals[name] = Signal()
        self._descriptions[name] = description
        self[name] = default
        self._defaults[name] = self[name]
        self._global_signal.send(self, name=name, value=self[name])

    def reset(self, name):
        """Reset setting `name` to default/initial value"""
        self[name] = self._defaults[name]

    def default(self, name):
        """Return settings default/initial value"""
        return self._defaults[name]

    def description(self, name):
        """Return setting's description"""
        return self._descriptions[name]

    def syntax(self, name):
        """Return setting's description"""
        return self._constructors[name].syntax

    def validate(self, name, value):
        """Pass `value` to `name`'s constructor and return the result"""
        if not isinstance(value, str) and isinstance(value, abc.Iterable):
            return self._constructors[name](*value)
        else:
            return self._constructors[name](value)

    def on_change(self, callback, name=None, autoremove=True):
        """
        Run `callback` every time a value changes

        If `name` is None, run `callback` if any signal changes.

        The signature of `callback` must be: (settings, name, value)

        If `autoremove` is True, stop calling `callback` once it is garbage
        collected.
        """
        if name is None:
            self._global_signal.connect(callback, weak=autoremove)
        else:
            self._signals[name].connect(callback, weak=autoremove)

    def __getitem__(self, name):
        return self._values[name]

    def __setitem__(self, name, value):
        value_ = self.validate(name, value)
        self._values[name] = value_
        self._global_signal.send(self, name=name, value=value_)
        self._signals[name].send(self, name=name, value=value_)

    def __contains__(self, name):
        return name in self._constructors

    def __iter__(self):
        return iter(self._constructors)

    def __len__(self):
        return len(self._constructors)
