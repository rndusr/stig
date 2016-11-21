import unittest
from stig.tui import theme
import io

import logging
log = logging.getLogger(__name__)


class Test_read(unittest.TestCase):
    def test_read_from_iterable(self):
        l = ('statusbar white on black',
             'loginform black on white')
        self.assertEqual(theme.read(l), list(l))

    def test_read_from_filehandle(self):
        fh = io.StringIO('statusbar white on black\n'
                         'loginform black on white')
        self.assertEqual(theme.read(fh), ['statusbar white on black',
                                          'loginform black on white'])


class TestPalette(unittest.TestCase):
    def test_ignore_comments(self):
        lines = ('# Comment',
                 'statusbar white on black',
                 '#Another comment',
                 'loginform black on white',
                 '  #  Final comment')
        pal = theme.Palette(lines)
        self.assertEqual(pal, [('statusbar', 'white', 'black'),
                               ('loginform', 'black', 'white')])

    def test_256_colors(self):
        lines = ('statusbar #fff on black',
                 'loginform black on #fff')
        pal = theme.Palette(lines)
        self.assertEqual(pal, [('statusbar', 'default', 'default', 'default', '#fff', 'black'),
                               ('loginform', 'default', 'default', 'default', 'black', '#fff')])
        self.assertEqual(pal.colors, 256)

    def test_invalid_16color(self):
        with self.assertRaises(theme.ThemeError) as cm:
            theme.Palette(('statusbar white on dark foo',))
        self.assertEqual(str(cm.exception), "Invalid color in line 1: 'dark foo'")

    def test_invalid_256color(self):
        with self.assertRaises(theme.ThemeError) as cm:
            theme.Palette(('statusbar: #1234 on dark green',))
        self.assertEqual(str(cm.exception), "Invalid color in line 1: '#1234'")

    def test_line_numbers_in_error_messages(self):
        with self.assertRaises(theme.ThemeError) as cm:
            theme.Palette(('# coment',
                           '# coment',
                           'statusbar white on black',
                           '# coment',
                           'loginform foo on black'))
        self.assertEqual(str(cm.exception), "Invalid color in line 5: 'foo'")

    def test_variable_declaration(self):
        lines = ('$var1 = black',
                 '$var2 = white',
                 'statusbar $var1 on $var2',
                 'loginform $var2 on $var1',
                 '$var1 = brown',
                 'something $var1 on $var2')
        self.assertEqual(theme.Palette(lines), [('statusbar', 'black', 'white'),
                                                ('loginform', 'white', 'black'),
                                                ('something', 'brown', 'white')])

    def test_set_default(self):
        default = ('statusbar white on black',
                   'loginform black on white')
        theme.set_default(theme.Palette(default))
        self.assertEqual(theme.DEFAULT_PALETTE, [('statusbar', 'white', 'black'),
                                                 ('loginform', 'black', 'white')])

    def test_validate(self):
        default = ('statusbar white on black',
                   'loginform black on white')
        theme.set_default(theme.Palette(default))
        with self.assertRaises(theme.ValidationError) as cm:
            theme.validate(theme.Palette(['loginform light green on dark green',
                                          'foobar    dark red    on light red']))
        self.assertEqual(str(cm.exception), "Invalid attribute name: 'foobar'")

        theme.validate(theme.Palette(['loginform light green on dark green',
                                      'statusbar dark red    on light red']))
