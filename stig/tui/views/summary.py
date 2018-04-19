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

from ...logging import make_logger
log = make_logger(__name__)

import urwid
from ..scroll import (ScrollBar, Scrollable)


def mksection(title, width, items):
    # Setting class variable 'title = title' below produces "NameError: name
    # 'title' is not defined"
    title_, width_ = title, width
    class Section(urwid.WidgetWrap):
        title = title_
        width = width_

        def __init__(self):
            value_widgets = {}
            needed_keys = set()
            rows = []
            label_width = max(len(item.label) for item in items)
            for item in items:
                label_w = urwid.Text(item.label.rjust(label_width))
                value_w = urwid.Text('')
                value_widgets[item] = value_w
                rows.append(urwid.Columns([('pack', label_w),
                                           ('pack', urwid.Text(': ')),
                                           value_w]))
                needed_keys.update(item.needed_keys)
            self._value_widgets = value_widgets
            self.needed_keys = needed_keys
            super().__init__(urwid.Pile(rows))

        def update(self, torrent):
            for item,value_w in self._value_widgets.items():
                value_w.set_text(item.human_readable(torrent))

    return Section


_sections = []
from ...views.summary import SECTIONS
for section in SECTIONS:
    sectionw = mksection(**section)
    _sections.append(sectionw)


class TorrentSummaryWidget(urwid.WidgetWrap):
    def __init__(self, srvapi, tid, title=None):
        self._title = title
        self._torrent = {}

        sections = []
        self._sections = {}
        for section_cls in _sections:
            section = section_cls()
            sections.append(section)
            self._sections[section.title] = section

        def add_title(title, section):
            header = urwid.Columns([('pack', urwid.Text('──┤ %s ├' % title)),
                                    urwid.Divider('─')])
            return urwid.Pile([('pack', header), section])

        grid = urwid.GridFlow([], cell_width=1, h_sep=3, v_sep=1, align='left')
        for section in sections:
            opts = grid.options('given', section.width)
            section_wrapped = add_title(section.title, section)
            grid.contents.append((section_wrapped, opts))
        self._grid = grid
        self._content = Scrollable(grid)

        super().__init__(urwid.AttrMap(
            ScrollBar(urwid.AttrMap(self._content, 'torrentsummary')),
            'scrollbar'
        ))

        # Register new request in request pool
        keys = set(('name',)).union(key for w in sections for key in w.needed_keys)
        self._poller = srvapi.create_poller(srvapi.torrent.torrents, (tid,), keys=keys)
        self._poller.on_response(self._handle_response)
        self._poller.on_error(self._handle_error)

    def _handle_response(self, response):
        if response is not None and response.success:
            self._torrent = response.torrents[0]
            self._content.original_widget = self._grid
            for w in self._sections.values():
                w.update(self._torrent)

            # Set new tab title if necessary
            if self.title_updater is not None:
                self.title_updater(self.title)
        elif response is not None:
            self._handle_error(*response.msgs)

    def _handle_error(self, *errors):
        self._torrent = {'name': None, 'id': None}
        pile = urwid.Pile(urwid.Text(('torrentsummary.error', str(e))) for e in errors)
        self._content.original_widget = pile

    @property
    def title(self):
        # self._title is user-specified title
        if self._title is not None:
            return self._title
        elif 'name' in self._torrent:
            return self._torrent['name']
        else:
            return 'No title'

    @property
    def focused_torrent_id(self):
        return self._torrent['id'] if 'id' in self._torrent else None
