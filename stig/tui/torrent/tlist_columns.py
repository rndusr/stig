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

"""Column classes that display information in torrent lists

Adding a new cell type adds a new optional column to torrent lists.  To do
this, write a new class that derives from CellWidgetBase and register it in
the COLUMNS dictionary to make it available.
"""

from ...logging import make_logger
log = make_logger(__name__)

import urwid

from ..table import ColumnHeaderWidget
from ...columns.tlist import COLUMNS


class Style():
    """Map standard attributes to those defined in a urwid palette

    prefix: common prefix of all attributes
    extras: additional attributes (e.g. 'header')
    modes: additional subsections with 'focused' and 'unfocused' attributes
           (e.g. 'highlighted')
    focusable: True if 'focused' attributes should be mapped, False otherwise
    """

    def __init__(self, prefix, modes=(), extras=(), focusable=True):
        self._attribs = {
            'unfocused': self.dotify(prefix, 'unfocused')
        }
        for extra in extras:
            self._attribs[extra] = self.dotify(prefix, extra)

        if focusable:
            self._attribs['focused'] = self.dotify(prefix, 'focused')

        for mode in modes:
            self._attribs[mode+'.focused'] = self.dotify(prefix, mode, 'focused')
            if focusable:
                self._attribs[mode+'.unfocused'] = self.dotify(prefix, mode, 'unfocused')

    def attrs(self, mode=None, focused=False):
        """Get attributes as specified in the urwid palette

        mode: one of the modes specified during initialization
        focused: If True the '...focused' attributes are returned,
                 '...unfocused otherwise
        """
        mode = '' if not mode else mode
        name = self.dotify(mode, 'focused' if focused else 'unfocused')
        if name in self._attribs:
            return self._attribs[name]
        else:
            return self._attribs[mode]

    @property
    def focus_map(self):
        """Map of all '...unfocused' -> '...focused' attributes"""
        focus_map = {}
        attribs = self._attribs
        for name in attribs:
            if name.endswith('unfocused'):
                name_focused = name[:-9] + 'focused'
                focus_map[attribs[name]] = attribs[name_focused]
        return focus_map

    @staticmethod
    def dotify(*strings):
        """Join non-empty strings with a '.'"""
        return '.'.join(x for x in (strings) if x)


# TODO: It would be great if some columns (e.g. rate-up/down) would shrink to
#       the widest visible value (including its header).  Other columns would
#       share the remaining width using ('weight', x), giving some of them
#       (e.g. name) more space than others (e.g. path).
import collections
class CellWidgetBase(urwid.WidgetWrap):
    style = collections.defaultdict(lambda key: 'default')
    header = urwid.Padding(urwid.Text('NO HEADER SPECIFIED'))
    width = ('weight', 100)
    align = 'right'

    def __init__(self):
        self.value = None
        self.text = urwid.Text('', wrap='clip', align=self.align)
        self.attrmap = urwid.AttrMap(self.text, self.style.attrs('unfocused'))
        return super().__init__(self.attrmap)

    def update(self, torrent):
        self.data = torrent
        new_value = self.get_value()
        if self.value != new_value:
            self.value = new_value
            self.text.set_text(str(new_value))
            attr = self.style.attrs(self.get_mode(), focused=False)
            self.attrmap.set_attr_map({None: attr})

    def get_value(self):
        raise NotImplementedError()

    def get_mode(self):
        return None


TUICOLUMNS = {}

import os
PATHSEP = os.sep
class Path(COLUMNS['path'], CellWidgetBase):
    width = 20
    style = Style(prefix='torrentlist.tpath', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['path'].header),
                           style.attrs('header'))

TUICOLUMNS['path'] = Path


class PeersConnected(COLUMNS['peers-connected'], CellWidgetBase):
    style = Style(prefix='torrentlist.peers-connected', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['peers-connected'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

TUICOLUMNS['peers-connected'] = PeersConnected


class PeersSeeding(COLUMNS['peers-seeding'], CellWidgetBase):
    style = Style(prefix='torrentlist.peers-seeding', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['peers-seeding'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 5 else ''

TUICOLUMNS['peers-seeding'] = PeersSeeding


class Progress(COLUMNS['progress'], CellWidgetBase):
    style = Style(prefix='torrentlist.progress', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['progress'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else ''

TUICOLUMNS['progress'] = Progress


class Ratio(COLUMNS['ratio'], CellWidgetBase):
    style = Style(prefix='torrentlist.ratio', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['ratio'].header),
                           style.attrs('header'))

    def get_mode(self):
        if 0 <= self.value < 1:
            return 'highlighted'

TUICOLUMNS['ratio'] = Ratio


class Size(COLUMNS['size'], CellWidgetBase):
    style = Style(prefix='torrentlist.size', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['size'].header),
                           style.attrs('header'))

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = COLUMNS['size'].header['right']

TUICOLUMNS['size'] = Size


class Downloaded(COLUMNS['downloaded'], CellWidgetBase):
    style = Style(prefix='torrentlist.downloaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['downloaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        t = self.data
        if t['%downloaded'] < 100 and 0 < t['size-downloaded'] < t['size-final']:
            return 'highlighted'

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = COLUMNS['downloaded'].header['right']

TUICOLUMNS['downloaded'] = Downloaded


class Uploaded(COLUMNS['uploaded'], CellWidgetBase):
    style = Style(prefix='torrentlist.uploaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['uploaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        if self.data['size-uploaded'] < self.data['size-downloaded']:
            return 'highlighted'

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = COLUMNS['uploaded'].header['right']

TUICOLUMNS['uploaded'] = Uploaded


class RateDown(COLUMNS['rate-down'], CellWidgetBase):
    style = Style(prefix='torrentlist.rate-down', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['rate-down'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = COLUMNS['rate-down'].header['right']

TUICOLUMNS['rate-down'] = RateDown


class RateUp(COLUMNS['rate-up'], CellWidgetBase):
    style = Style(prefix='torrentlist.rate-up', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['rate-up'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = COLUMNS['rate-up'].header['right']

TUICOLUMNS['rate-up'] = RateUp


class EtaComplete(COLUMNS['eta'], CellWidgetBase):
    style = Style(prefix='torrentlist.eta', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['eta'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

TUICOLUMNS['eta'] = EtaComplete


class TorrentName(COLUMNS['name'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='torrentlist.name', focusable=True, extras=('header',),
                  modes=('idle.progress1', 'idle.progress2', 'idle.complete',
                         'stopped.progress1', 'stopped.progress2', 'stopped.complete',
                         'isolated.progress1', 'isolated.progress2', 'isolated.complete',
                         'initializing.progress1', 'initializing.progress2', 'initializing.complete',
                         'verifying.progress1', 'verifying.progress2', 'verifying.complete',
                         'downloading.progress1', 'downloading.progress2', 'downloading.complete',
                         'uploading.progress1', 'uploading.progress2', 'uploading.complete',
                         'queued.progress1', 'queued.progress2', 'queued.complete',
                         'connected.progress1', 'connected.progress2', 'connected.complete'))
    header = urwid.AttrMap(ColumnHeaderWidget(**COLUMNS['name'].header),
                           style.attrs('header'))
    needed_keys = ('name', 'status', '%downloaded', '%verified', '%metadata',
                   'isolated', 'rate-up', 'rate-down', 'peers-connected')

    def __init__(self, *args, **kwargs):
        self.status = ('', 'idle', 0)
        super().__init__(*args, **kwargs)

    def update(self, torrent):
        new_status = self.make_status(torrent)
        if new_status != self.status:
            self.status = new_status
            self._invalidate()

    def render(self, size, focus=False):
        (maxcol,) = size
        name, mode, progress = self.status
        name = name[:maxcol].ljust(maxcol, ' ')  # Expand/Shrink name to full width
        if progress == 100:
            attrs = self.style.attrs(mode+'.complete', focused=focus)
            self.text.set_text((attrs, name))
        else:
            completed_col = int(maxcol * progress / 100)  # Width of first part of progress bar
            name1 = name[:completed_col]
            name2 = name[completed_col:]
            attrs1 = self.style.attrs(mode+'.progress1', focused=focus)
            attrs2 = self.style.attrs(mode+'.progress2', focused=focus)
            self.text.set_text([(attrs1, name1),
                                (attrs2, name2)])
        return super().render(size, focus)

    def get_mode(self):
        return self.status[1]

    @staticmethod
    def make_status(t):
        progress = t['%downloaded']
        if t['status'] == 'stopped':
            mode = 'stopped'
        elif t['isolated']:
            mode = 'isolated'
        elif t['%metadata'] < 1:
            mode = 'initializing'
            progress = t['%metadata']
        elif 'verify' in t['status']:
            mode = 'verifying'
            progress = t['%verified']
        elif t['rate-down'] > 0 and t['status'] == 'leeching':
            mode = 'downloading'
        elif t['status'] == 'leeching pending':
            mode = 'queued'
        elif t['rate-up'] > 0:
            mode = 'uploading'
        elif t['peers-connected'] > 0:
            mode = 'connected'
        else:
            mode = 'idle'
        return (t['name'], mode, progress)

TUICOLUMNS['name'] = TorrentName
