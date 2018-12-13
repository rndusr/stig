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


class CallbackDict(dict):
    """Mapping that runs a callback on every change"""
    # https://stackoverflow.com/a/5186698

    __slots__ = ["callback"]

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        dict.__init__(self, *args, **kwargs)

    def _wrap(method):
        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            self.callback()
            return result
        return wrapper

    __delitem__ = _wrap(dict.__delitem__)
    __setitem__ = _wrap(dict.__setitem__)
    clear = _wrap(dict.clear)
    pop = _wrap(dict.pop)
    popitem = _wrap(dict.popitem)
    setdefault = _wrap(dict.setdefault)
    update = _wrap(dict.update)



from collections import abc
class AliasDict(abc.MutableMapping):
    """Use multiple keys to get the same value"""
    def __init__(self, dct=None, **kwargs):
        self._dct = dct if dct is not None else {}
        self._dct.update(kwargs)
        for key in self._dct:
            assert self._is_valid_key(key)

    def __getitem__(self, key):
        for keys,value in self._dct.items():
            if key in keys:
                return value
        raise KeyError(key)

    def __setitem__(self, key, value):
        for keys in self._dct:
            if key in keys:
                key = keys
        if not self._is_valid_key(key):
            key = (key,)
        self._dct[key] = value

    def __delitem__(self, key):
        for keys,value in self._dct.items():
            if key in keys:
                del self._dct[keys]

    @staticmethod
    def _is_valid_key(key):
        return isinstance(key, (tuple, frozenset))

    def __iter__(self):
        return iter(self._dct)

    def __len__(self):
        return len(self._dct)

    def __repr__(self):
        return repr(self._dct)


from collections import abc
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
    Log messages to `logger`

    `msgs` is an iterable of strings or exceptions.  Strings are logged to
    level INFO, exceptions are logged to level ERROR.

    If `quiet` evaluates to True, INFO messages are not logged.
    """
    if not quiet:
        for msg in response.msgs:
            process.info(msg)

    for error in response.errors:
        process.error(error)
