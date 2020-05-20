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

import functools
import itertools

from . import Candidate, Candidates
from ..client import filters as filter_clses
from ..client import sorters as sorter_clses

columns_labels = {'torrents' : 'Torrent List Column',
                  'files'    : 'File List Column',
                  'peers'    : 'Peer List Column',
                  'trackers' : 'Tracker List Column',
                  'settings' : 'Setting List Column'}


sorters_labels = {'TorrentSorter' : 'Torrent Sort Order',
                  'PeerSorter'    : 'Peer Sort Order',
                  'TrackerSorter' : 'Tracker Sort Order',
                  'SettingSorter' : 'Setting Sort Order'}


@functools.lru_cache(maxsize=None)
def get_sorter_cls(clsname):
    return getattr(sorter_clses, clsname)


# All filters use the same operators
filter_compare_ops = filter_clses.TorrentFilter.POSSIBLE_OPERATORS
filter_combine_ops = ('&', '|')
filter_labels = {'TorrentFilter'  : 'Torrent Filter',
                 'FileFilter'    : 'File Filter',
                 'PeerFilter'    : 'Peer Filter',
                 'TrackerFilter' : 'Tracker Filter',
                 'SettingFilter' : 'Setting Filter'}

@functools.lru_cache(maxsize=None)
def filter_names(filter_cls_name):
    """Filter names as Candidate instances with description and aliases"""
    def get_names(filter_cls):
        for name in get_filter_names(filter_cls):
            filter_spec = get_filter_spec(filter_cls, name)
            desc = filter_spec.description
            alias_str = ','.join(filter_spec.aliases)
            yield Candidate(name, in_parens=alias_str, Description=desc)

    filter_cls = get_filter_cls(filter_cls_name)
    curarg_seps = itertools.chain(filter_compare_ops, filter_combine_ops, (filter_cls.INVERT_CHAR,))
    return Candidates(get_names(filter_cls),
                      curarg_seps=curarg_seps,
                      label=filter_labels[filter_cls_name])

@functools.lru_cache(maxsize=None)
def get_filter_cls(name):
    try:
        return getattr(filter_clses, name)
    except AttributeError:
        raise ValueError('Not a filter class: %r' % name)

@functools.lru_cache(maxsize=None)
def get_filter_names(filter_cls):
    return itertools.chain(filter_cls.BOOLEAN_FILTERS,
                           filter_cls.COMPARATIVE_FILTERS)

@functools.lru_cache(maxsize=None)
def get_filter_spec(filter_cls, name):
    try:
        return filter_cls.BOOLEAN_FILTERS[name]
    except KeyError:
        try:
            return filter_cls.COMPARATIVE_FILTERS[name]
        except KeyError:
            raise ValueError('No such filter: %r' % (name,))

@functools.lru_cache(maxsize=None)
def filter_takes_completable_values(filter_cls, name):
    try:
        filter_spec = get_filter_spec(filter_cls, name)
    except ValueError:
        return False
    else:
        return (name in filter_cls.COMPARATIVE_FILTERS and
                filter_spec is not None and
                issubclass(filter_spec.value_type, str))



def find_subtree(torrent, path):
    """
    `torrent` must be a Torrent instance and `path` must be a sequence of nested
    directory names in the tree `torrent['files']`

    Empty strings in `path` are ignored (like `ls foo//bar///baz` also works).

    If `torrent` is a single-file torrent or any item in `path[:-1]` points to a
    leaf or doesn't exist, return None.  Otherwise, return the subtree or
    file/leaf that `path` points to.  (To clarify: the last item in `path` may
    not exist, in which case its parent tree is returned.)
    """
    tree = torrent['files'][torrent['name']]
    if tree.nodetype == 'leaf':
        # `torrent` is single-file torrent
        return None
    else:
        for i,part in enumerate(path):
            if part:
                subtree = tree.get(part)
                is_last_part = i == len(path) - 1
                if subtree is None:
                    if not is_last_part:
                        return None
                elif subtree.nodetype == 'leaf' and is_last_part:
                    return subtree
                elif subtree.nodetype == 'parent':
                    tree = subtree
                else:
                    # An item in `path[:-1]` points to a leaf.  We can't use
                    # files as subtrees.
                    return None
        return tree

def find_files(tree):
    """Files at TorrentFileTree object `tree`"""
    for item in tree:
        if tree[item].nodetype == 'leaf':
            yield item

def find_dirs(tree):
    """Directories at TorrentFileTree object `tree`"""
    for item in tree:
        if tree[item].nodetype == 'parent':
            yield item
