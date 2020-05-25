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

import itertools
from collections import abc, defaultdict

from blinker import Signal

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class Settings(abc.Mapping):
    """Typed user configuration settings"""

    def __init__(self):
        self._defaults = {}
        self._values = {}
        self._constructors = {}
        self._getters = defaultdict(lambda: None)
        self._setters = defaultdict(lambda: None)
        self._descriptions = {}
        self._signals = defaultdict(lambda: Signal())
        self._global_signal = Signal()

    def add(self, name, constructor, default, description=None, getter=None, setter=None):
        """
        Add new setting

        name:        Identifier for this setting
        constructor: Callable that takes one argument and returns a new value
                     for this setting
        default:     Initial and default value
        description: What the setting does
        getter:      Callable with no arguments that returns the value
        setter:      Callable with one argument that sets the value
        """
        self._constructors[name] = constructor
        self._descriptions[name] = description
        value_ = self.validate(name, default)
        self._values[name] = value_
        self._defaults[name] = value_
        if getter:
            self._getters[name] = getter
        if setter:
            self._setters[name] = setter
        self._global_signal.send(self, name=name, value=value_)

    def reset(self, name):
        """Reset setting `name` to default/initial value"""
        self[name] = self._defaults[name]

    def default(self, name):
        """Return setting's default/initial value"""
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

        If `name` is None, run `callback` after every change.

        The signature of `callback` must be: (settings, name, value)

        If `autoremove` is True, stop calling `callback` once it is garbage
        collected.
        """
        if name is None:
            self._global_signal.connect(callback, weak=autoremove)
        else:
            self._signals[name].connect(callback, weak=autoremove)

    @property
    def as_dict(self):
        # NOTE 1: The "id" key is important because filters (including
        #         SettingFilter) expect it.  This requirement can possibly
        #         removed but it probably means rewriting lots of filter tests.
        # NOTE 2: The "validate" lambda MUST store the value of `name`,
        #         otherwise `self.validate` always gets called with the for
        #         loop's last `name` value.
        return {name:{'id': name,
                      'value': self[name],
                      'default': self.default(name),
                      'description': self.description(name),
                      'syntax': self.syntax(name),
                      'validate': lambda v, n=name: self.validate(n, v)}
                for name,value in self.items()}

    def __getitem__(self, name):
        getter = self._getters[name]
        if getter is not None:
            return self.validate(name, getter())
        else:
            return self._values[name]

    def __setitem__(self, name, value):
        value_ = self.validate(name, value)
        setter = self._setters[name]
        if setter is not None:
            setter(value_)
        else:
            self._values[name] = value_
        self._global_signal.send(self, name=name, value=value_)
        self._signals[name].send(self, name=name, value=value_)

    def __contains__(self, name):
        return name in self._constructors

    def __iter__(self):
        return iter(self._constructors)

    def __len__(self):
        return len(self._constructors)


class RemoteSettings(abc.Mapping):
    """
    Thin wrapper around client.SettingsAPI that transparently adds/removes "srv." from
    keys and provides an interface similar to the Settings class
    """
    def __init__(self, remotecfg):
        self._cfg = remotecfg

    # Forward calls to SettingsAPI object

    def poll(self):
        """Get current values from server soon"""
        self._cfg.poll()

    async def update(self):
        """Get current values from server"""
        await self._cfg.update()

    async def set(self, name, value):
        """Change setting on the server"""
        if not name.startswith('srv.'):
            raise KeyError(name)
        await self._cfg.set(name[4:], value)

    def on_update(self, callback, autoremove=True):
        """Run `callback` after settings are updated"""
        return self._cfg.on_update(callback, autoremove=autoremove)

    def on_change(self, callback, name=None, autoremove=True):
        """
        Run `callback` every time a value is changed

        If `name` is None, run `callback` after every change.

        The signature of `callback` must be: (settings, name, value)

        If `autoremove` is True, stop calling `callback` once it is garbage
        collected.
        """
        self._cfg.on_set(callback, key=name, autoremove=autoremove)

    # Settings class protocol

    def reset(self, name):
        """Reset setting `name` to default/initial value"""
        if not name.startswith('srv.'):
            raise KeyError(name)
        raise NotImplementedError()

    def default(self, name):
        """Return setting's default/initial value"""
        if not name.startswith('srv.'):
            raise KeyError(name)
        return self._cfg.default(name[4:])

    def description(self, name):
        """Return setting's description"""
        if not name.startswith('srv.'):
            raise KeyError(name)
        return self._cfg.description(name[4:])

    def syntax(self, name):
        """Return setting's description"""
        if not name.startswith('srv.'):
            raise KeyError(name)
        return self._cfg.syntax(name[4:])

    def validate(self, name, value):
        """Pass `value` to `name`'s constructor and return the result"""
        if not name.startswith('srv.'):
            raise KeyError(name)
        return self._cfg.validate(name[4:], value)

    @property
    def as_dict(self):
        return {'srv.' + name: {**setting, 'id': 'srv.' + name}
                for name,setting in self._cfg.as_dict.items()}

    def __getitem__(self, name):
        if not name.startswith('srv.'):
            raise KeyError(name)
        return self._cfg[name[4:]]

    def __contains__(self, name):
        if not name.startswith('srv.'):
            return False
        return name[4:] in self._cfg

    def __iter__(self):
        return iter('srv.' + name for name in self._cfg)

    def __len__(self):
        return len(self._cfg)


class CombinedSettings(abc.Mapping):
    """
    Combination of Settings and RemoteSettings instances
    """
    def __init__(self, local, remote):
        self._local = local
        self._remote = remote

    def is_local(self, name):
        return not name.startswith('srv.')

    def is_remote(self, name):
        return name.startswith('srv.')

    async def update(self):
        """Get current remote settings from server"""
        await self._remote.update()

    async def set(self, name, value):
        if name in self._local:
            self._local[name] = value
        elif name in self._remote:
            await self._remote.set(name, value)
        else:
            raise KeyError(name)

    def _find(self, name):
        if name in self._local:
            return self._local
        elif name in self._remote:
            return self._remote
        else:
            raise KeyError(name)

    def reset(self, name):
        """Reset setting `name` to default/initial value"""
        return self._find(name).reset(name)

    def default(self, name):
        """Return setting's default/initial value"""
        return self._find(name).default(name)

    def description(self, name):
        """Return setting's description"""
        return self._find(name).description(name)

    def syntax(self, name):
        """Return setting's description"""
        return self._find(name).syntax(name)

    def validate(self, name, value):
        """Pass `value` to `name`'s constructor and return the result"""
        return self._find(name).validate(name, value)

    @property
    def as_dict(self):
        return {**self._local.as_dict, **self._remote.as_dict}

    def __getitem__(self, name):
        return self._find(name)[name]

    def __setitem__(self, name, value):
        self._find(name)[name] = value

    def __contains__(self, name):
        return name in self._local or name in self._remote

    def __iter__(self):
        return iter(itertools.chain(self._local, self._remote))

    def __len__(self):
        return len(self._local) + len(self._remote)
