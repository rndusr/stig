from stig.tui.scroll import (Scrollable, ScrollBar)

import unittest
import urwid

from .resources_tui import get_canvas_text

TEXT = ('one',
        'two',
        'three',
        'four',
        'five',
        'six',
        'seven',
        'eight',
        'nine',
        'ten')


class FixedText(urwid.Widget):
    _sizing = frozenset(['fixed'])

    def __init__(self):
        self._canvas = urwid.Text('\n'.join(TEXT)).render((10,))

    def pack(self, size=None, focus=False):
        return self._canvas.cols(), self._canvas.rows()

    def render(self, size, focus=False):
        return self._canvas


class TestScrollable(unittest.TestCase):
    def setUp(self):
        self._test_widgets = (
            Scrollable(FixedText()),
            Scrollable(urwid.Text('\n'.join(TEXT), wrap='clip')),
        )

    def check(self, widget, size, text, cursor_pos=()):
        maxcol, maxrow = size
        canv = widget.render(size, focus=True)
        self.assertEqual((canv.cols(), canv.rows()), size)

        content = tuple(get_canvas_text(row) for row in canv.content())
        content_exp = tuple(text)
        self.assertEqual(content, content_exp)

        if cursor_pos != ():
            self.assertEqual(canv.cursor, cursor_pos)


    def test_empty_widget(self):
        for w in (Scrollable(urwid.Text('')),
                  Scrollable(urwid.Pile([]))):
            self.check(w, size=(5, 10), text=(' '*5,)*10)
            self.check(w, size=(5, 10), text=(' '*5,)*10)
            self.assertEqual(w.get_scrollpos((5, 10), focus=True), 0)
            self.assertEqual(w.get_scrollpos((5, 10), focus=False), 0)

    def test_perfect_fit(self):
        for w in self._test_widgets:
            self.check(w, size=(5, 10),
                       text=(l.ljust(5) for l in TEXT))

    def test_horizontal_padding(self):
        for w in self._test_widgets:
            self.check(w, size=(15, 10),
                       text=(l.ljust(15) for l in TEXT))

    def test_vertical_padding(self):
        for w in self._test_widgets:
            self.check(w, size=(10, 15),
                       text=(l.ljust(10) for l in TEXT+('',)*5))

    def test_horizontal_trimming(self):
        for w in self._test_widgets:
            self.check(w, size=(3, 10),
                       text=(l[:3].ljust(3) for l in TEXT))

    def test_vertical_trimming(self):
        for w in self._test_widgets:
            self.check(w, size=(10, 3),
                       text=(l.ljust(10) for l in TEXT[:3]))


    def test_set_position_positive(self):
        size = (10, 3)
        for w in self._test_widgets:
            for i in range(len(TEXT)*2):
                w.set_scrollpos(i)
                start = min(len(TEXT)-size[1], i)
                end   = min(len(TEXT),         i+size[1])
                self.check(w, size,
                           text=(l.ljust(size[0]) for l in TEXT[start:end]))

    def test_set_position_negative(self):
        size = (10, 3)
        for w in self._test_widgets:
            for i in range(len(TEXT)*2):
                pos = -i-1
                w.set_scrollpos(pos)
                start = max(0, -i + len(TEXT) - size[1])
                end   = start + size[1]
                self.check(w, size,
                           text=(l.ljust(size[0]) for l in TEXT[start:end]))


    def test_scroll_line_down(self):
        size = (10, 3)
        for w in self._test_widgets:
            for i in range(21):
                x = min(len(TEXT)-size[1], i)
                y = min(len(TEXT),         i+size[1])
                self.check(w, size,
                           text=(l.ljust(10) for l in TEXT[x:y]))
                self.assertEqual(w.get_scrollpos(size), x)
                w.keypress(size, 'down')

    def test_scroll_line_up(self):
        size = (10, 3)
        for w in self._test_widgets:
            w.set_scrollpos(len(TEXT)-1)  # jump to end
            for i in reversed(range(21)):
                i -= 10
                x = max(0, i-size[1])
                y = max(size[1], i)
                self.check(w, size,
                           text=(l.ljust(10) for l in TEXT[x:y]))
                self.assertEqual(w.get_scrollpos(size), x)
                w.keypress(size, 'up')

    def test_scroll_page_down(self):
        size = (10, 3)
        for w in self._test_widgets:
            for i in range(0, 21, size[1]-1):
                x = min(len(TEXT)-size[1], i)
                y = min(len(TEXT),         i+size[1])
                self.check(w, size,
                           text=(l.ljust(10) for l in TEXT[x:y]))
                self.assertEqual(w.get_scrollpos(size), x)
                w.keypress(size, 'page down')

    def test_scroll_page_up(self):
        size = (10, 3)
        for w in self._test_widgets:
            w.set_scrollpos(len(TEXT)-1)  # jump to end
            for i in reversed(range(0, 21, size[1]-1)):
                i -= 10
                x = max(0, i-size[1])
                y = max(size[1], i)
                self.check(w, size,
                           text=(l.ljust(10) for l in TEXT[x:y]))
                self.assertEqual(w.get_scrollpos(size), x)
                w.keypress(size, 'page up')


    def test_widget_with_cursor_gets_keypress_only_if_visible(self):
        w = Scrollable(
            urwid.Pile([urwid.Text('t1'),
                        urwid.Text('t2'),
                        urwid.Edit('', 'e3')])
        )
        size = (5, 2)

        def press_keys():
            for key in ('backspace', 'backspace', 'f', 'o', 'o'):
                w.keypress(size, key)

        self.check(w, size, text=('t1'.ljust(size[0]),
                                  't2'.ljust(size[0])))
        press_keys()
        self.check(w, size, text=('t1'.ljust(size[0]),
                                  't2'.ljust(size[0])))

        w.set_scrollpos(1)
        self.check(w, size, text=('t2'.ljust(size[0]),
                                  'e3'.ljust(size[0])))
        press_keys()
        self.check(w, size, text=('t2'.ljust(size[0]),
                                  'foo'.ljust(size[0])))

    # This test is disabled intentionally. See the FIXME at the end of
    # Scrollable.render().
    # def test_selectable_widget_gets_keypress_only_if_visible(self):
    #     class HungryText(urwid.Text):
    #         def selectable(self):
    #             return True

    #         def keypress(self, size, key):
    #             self.set_text(self.text + key)

    #     h = HungryText('123')
    #     w = Scrollable(
    #         urwid.Pile([urwid.Text('wrap this'),
    #                     urwid.Text('t2'),
    #                     h])
    #     )
    #     size = (4, 3)

    #     def send_text(keys):
    #         for key in keys:
    #             w.keypress(size, key)

    #     self.check(w, size, text=('wrap'.ljust(size[0]),
    #                               'this'.ljust(size[0]),
    #                               't2'.ljust(size[0])))
    #     send_text('4')
    #     self.check(w, size, text=('wrap'.ljust(size[0]),
    #                               'this'.ljust(size[0]),
    #                               't2'.ljust(size[0])))
    #     self.assertEqual(h.text, '123')

    #     w.set_scrollpos(1)
    #     self.check(w, size, text=('this'.ljust(size[0]),
    #                               't2'.ljust(size[0]),
    #                               '123'.ljust(size[0])))
    #     send_text('4')
    #     self.check(w, size, text=('this'.ljust(size[0]),
    #                               't2'.ljust(size[0]),
    #                               '1234'.ljust(size[0])))
    #     self.assertEqual(h.text, '1234')

    def test_moving_focus_up_down(self):
        w = Scrollable(
            urwid.Pile([urwid.Text('t1'),
                        urwid.Text('t2'),
                        urwid.Edit('', 'e3'),
                        urwid.Text('t4'),
                        urwid.Text('t5'),
                        urwid.Edit('', 'e6'),
                        urwid.Text('t7'),
                        urwid.Text('t8')])
        )
        size = (10, 2)
        self.check(w, size, text=('t1'.ljust(size[0]),
                                  't2'.ljust(size[0])))
        w.keypress(size, 'down')
        self.check(w, size, text=('t2'.ljust(size[0]),
                                  'e3'.ljust(size[0])))
        w.keypress(size, 'down')
        self.check(w, size, text=('t5'.ljust(size[0]),
                                  'e6'.ljust(size[0])))
        w.keypress(size, 'down')
        self.check(w, size, text=('e6'.ljust(size[0]),
                                  't7'.ljust(size[0])))
        w.keypress(size, 'down')
        self.check(w, size, text=('t7'.ljust(size[0]),
                                  't8'.ljust(size[0])))

    def test_mouse_event(self):
        w = Scrollable(
            urwid.Pile([urwid.Text('t1'),
                        urwid.Text('t2'),
                        urwid.Edit('', 'eXXX'),
                        urwid.Text('t3'),
                        urwid.Edit('', 'eYYY'),
                        urwid.Text('t4'),
                        urwid.Text('t5')])
        )
        size = (10, 2)
        self.check(w, size, cursor_pos=None, text=('t1'.ljust(size[0]),
                                                   't2'.ljust(size[0])))

        size = (10, 5)
        self.check(w, size, cursor_pos=(4, 2), text=('t1'.ljust(size[0]),
                                                     't2'.ljust(size[0]),
                                                     'eXXX'.ljust(size[0]),
                                                     't3'.ljust(size[0]),
                                                     'eYYY'.ljust(size[0])))

        w.mouse_event(size, 'mouse press', button=1, col=2, row=4, focus=True)
        self.check(w, size, cursor_pos=(2, 4), text=('t1'.ljust(size[0]),
                                                     't2'.ljust(size[0]),
                                                     'eXXX'.ljust(size[0]),
                                                     't3'.ljust(size[0]),
                                                     'eYYY'.ljust(size[0])))

        w.set_scrollpos(2)
        w.mouse_event(size, 'mouse press', button=1, col=3, row=2, focus=True)
        self.check(w, size, cursor_pos=(3, 2), text=('eXXX'.ljust(size[0]),
                                                     't3'.ljust(size[0]),
                                                     'eYYY'.ljust(size[0]),
                                                     't4'.ljust(size[0]),
                                                     't5'.ljust(size[0])))

        w.mouse_event(size, 'mouse press', button=1, col=4, row=0, focus=True)
        self.check(w, size, cursor_pos=(4, 0), text=('eXXX'.ljust(size[0]),
                                                     't3'.ljust(size[0]),
                                                     'eYYY'.ljust(size[0]),
                                                     't4'.ljust(size[0]),
                                                     't5'.ljust(size[0])))



class TestScrollBarWithScrollable(unittest.TestCase):
    def setUp(self):
        self.pile = urwid.Pile([
            urwid.Text(l) for l in TEXT
        ])
        self.scrollable = Scrollable(self.pile)
        self.scrollbar = ScrollBar(self.scrollable,
                                   thumb_char='#', trough_char='|')

    def check(self, widget, size, text, cursor_pos=()):
        canv = widget.render(size, focus=True)
        self.assertEqual((canv.cols(), canv.rows()), size)

        content = tuple(get_canvas_text(row) for row in canv.content())
        content_exp = tuple(text)
        self.assertEqual(content, content_exp)

        if cursor_pos != ():
            self.assertEqual(canv.cursor, cursor_pos)


    def test_empty_widget(self):
        for w in (ScrollBar(Scrollable(urwid.Text(''))),
                  ScrollBar(Scrollable(urwid.Pile([])))):
            self.check(w, size=(5, 10), text=(' '*5,)*10)

    def test_scrollbar_grows_and_shrinks(self):
        size = (10, 3)
        self.check(self.scrollbar, size,
                   text=('one'.ljust(size[0]-1)   + '#',
                         'two'.ljust(size[0]-1)   + '|',
                         'three'.ljust(size[0]-1) + '|'))
        size = (10, 6)
        self.check(self.scrollbar, size,
                   text=('one'.ljust(size[0]-1)   + '#',
                         'two'.ljust(size[0]-1)   + '#',
                         'three'.ljust(size[0]-1) + '#',
                         'four'.ljust(size[0]-1)  + '#',
                         'five'.ljust(size[0]-1)  + '|',
                         'six'.ljust(size[0]-1)   + '|'))

    def test_scrollbar_disappears_if_not_needed(self):
        size = (10, 10)
        self.check(self.scrollbar, size,
                   text=(t.ljust(size[0])
                         for t in TEXT))

    def test_big_scrollbar_moves_up_and_down(self):
        size = (10, 6)
        self.check(self.scrollbar, size,
                   text=('one'.ljust(size[0]-1)     + '#',
                         'two'.ljust(size[0]-1)     + '#',
                         'three'.ljust(size[0]-1)   + '#',
                         'four'.ljust(size[0]-1)    + '#',
                         'five'.ljust(size[0]-1)    + '|',
                         'six'.ljust(size[0]-1)     + '|'))

        self.scrollable.set_scrollpos(len(self.pile.contents)-1)
        self.check(self.scrollbar, size,
                   text=('five'.ljust(size[0]-1)    + '|',
                         'six'.ljust(size[0]-1)     + '|',
                         'seven'.ljust(size[0]-1)   + '#',
                         'eight'.ljust(size[0]-1)   + '#',
                         'nine'.ljust(size[0]-1)    + '#',
                         'ten'.ljust(size[0]-1)     + '#'))

        self.scrollable.set_scrollpos(int((len(self.pile.contents)-size[1])/2))
        self.check(self.scrollbar, size,
                   text=('three'.ljust(size[0]-1)   + '|',
                         'four'.ljust(size[0]-1)    + '#',
                         'five'.ljust(size[0]-1)    + '#',
                         'six'.ljust(size[0]-1)     + '#',
                         'seven'.ljust(size[0]-1)   + '#',
                         'eight'.ljust(size[0]-1)   + '|'))

    def test_small_scrollbar_moves_up_and_down(self):
        size = (10, 3)
        self.check(self.scrollbar, size,
                   text=('one'.ljust(size[0]-1)     + '#',
                         'two'.ljust(size[0]-1)     + '|',
                         'three'.ljust(size[0]-1)   + '|'))

        self.scrollable.set_scrollpos(len(self.pile.contents)-1)
        self.check(self.scrollbar, size,
                   text=('eight'.ljust(size[0]-1)   + '|',
                         'nine'.ljust(size[0]-1)    + '|',
                         'ten'.ljust(size[0]-1)     + '#'))

        self.scrollable.set_scrollpos(int((len(self.pile.contents)-size[1])/2))
        self.check(self.scrollbar, size,
                   text=('four'.ljust(size[0]-1)    + '|',
                         'five'.ljust(size[0]-1)    + '#',
                         'six'.ljust(size[0]-1)     + '|'))


    def test_mouse_event(self):
        scrl = Scrollable(
            urwid.Pile([urwid.Text('t1'),
                        urwid.Text('t2'),
                        urwid.Edit('', 'eXXX'),
                        urwid.Text('t3'),
                        urwid.Edit('', 'eYYY'),
                        urwid.Text('t4'),
                        urwid.Text('t5')])
        )
        sb = ScrollBar(scrl, thumb_char='#', trough_char='|')

        size = (10, 5)
        self.check(sb, size, cursor_pos=(4, 2), text=('t1'.ljust(size[0]-1)   + '#',
                                                      't2'.ljust(size[0]-1)   + '#',
                                                      'eXXX'.ljust(size[0]-1) + '#',
                                                      't3'.ljust(size[0]-1)   + '#',
                                                      'eYYY'.ljust(size[0]-1) + '|'))

        sb.mouse_event(size, 'mouse press', button=1, col=1, row=4, focus=True)
        self.check(sb, size, cursor_pos=(1, 4), text=('t1'.ljust(size[0]-1)   + '#',
                                                      't2'.ljust(size[0]-1)   + '#',
                                                      'eXXX'.ljust(size[0]-1) + '#',
                                                      't3'.ljust(size[0]-1)   + '#',
                                                      'eYYY'.ljust(size[0]-1) + '|'))

        scrl.set_scrollpos(2)
        self.check(sb, size, cursor_pos=(1, 2), text=('eXXX'.ljust(size[0]-1) + '|',
                                                      't3'.ljust(size[0]-1)   + '#',
                                                      'eYYY'.ljust(size[0]-1) + '#',
                                                      't4'.ljust(size[0]-1)   + '#',
                                                      't5'.ljust(size[0]-1)   + '#'))

        sb.mouse_event(size, 'mouse press', button=1, col=3, row=0, focus=True)
        self.check(sb, size, cursor_pos=(3, 0), text=('eXXX'.ljust(size[0]-1) + '|',
                                                      't3'.ljust(size[0]-1)   + '#',
                                                      'eYYY'.ljust(size[0]-1) + '#',
                                                      't4'.ljust(size[0]-1)   + '#',
                                                      't5'.ljust(size[0]-1)   + '#'))

    def test_shards_bug(self):
        scrl = Scrollable(
            urwid.Pile([urwid.Columns([urwid.Text("text")] * 3)] * 3)
        )
        sb = ScrollBar(scrl, thumb_char='#', trough_char='|', width=3)
        area = urwid.Overlay(urwid.SolidFill("O"), sb, "center", 4, "middle", 5)

        self.check(area, (10, 5), cursor_pos=(), text=(
            'tetOOOO###',
            'xttOOOO###',
            'tetOOOO###',
            'xttOOOO###',
            'tetOOOO|||',
        ))

    def test_wrapping_bug(self):
        scrl = Scrollable(
            urwid.Pile([urwid.Columns([urwid.Text("long text")] * 2)] * 2)
        )
        sb = ScrollBar(scrl, thumb_char='#', trough_char='|', width=3)
        widget = urwid.Columns([urwid.Pile([urwid.LineBox(sb)])] * 2)

        self.check(widget, (9, 6), cursor_pos=(), text=(
            '┌───┐┌──┐',
            '│###││##│',
            '│###││##│',
            '│###││##│',
            '│###││##│',
            '└───┘└──┘',
        ))
