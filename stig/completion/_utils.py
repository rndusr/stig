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

from . import Candidates


def find_subtree(torrent, path):
    """
    `torrent` must be a Torrent instance and `path` must be a list of nested
    directory names in the tree `torrent['files']`

    Return the subtree at `path` or None if `path` points to a leaf/file
    """
    if len(tuple(torrent['files'].directories)) <= 0:
        log.debug('No directories in %r', torrent['files'])
    else:
        tree = torrent['files'][torrent['name']]
        for i,part in enumerate(path):
            if part:
                subtree = tree.get(part)
                is_last_part = i == len(path)-1
                if subtree is None:
                    log.debug('%r not found in %r', part, tree)
                    if is_last_part:
                        log.debug('  thats ok, its the last part')
                    else:
                        log.debug('  thats not ok, its not the last part')
                        return None
                elif subtree.nodetype == 'leaf' and is_last_part:
                    log.debug('Found leaf: %r', subtree)
                    return subtree
                elif subtree.nodetype == 'parent':
                    tree = subtree
                else:
                    log.debug('  aborting resolution of weird path at %r', part)
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
