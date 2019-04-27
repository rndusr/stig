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

from . import Candidates


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
                is_last_part = i == len(path)-1
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
