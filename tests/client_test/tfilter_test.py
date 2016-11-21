from stig.client.tfilter import (_TorrentFilter, TorrentFilter)
from stig.client.aiotransmission.torrent import Torrent

import unittest


tlist = (
    Torrent({'id': 1, 'name': 'Foo', 'downloadDir': '/some/path/to/torrents',
             'isStalled': True, 'isPrivate': False, 'status': 6, 'percentDone': 1,
             'peersConnected': 0, 'rateUpload': 0, 'rateDownload': 0, 'downloadedEver': 0}),
    Torrent({'id': 2, 'name': 'Bar123', 'downloadDir': '/some/path/to/torrents',
             'isStalled': False, 'isPrivate': True, 'status': 4, 'percentDone': 0.0235,
             'peersConnected': 3, 'rateUpload': 58e3, 'rateDownload': 384e3, 'downloadedEver': 0}),
    Torrent({'id': 3, 'name': 'Fim', 'downloadDir': '/other/path/to/torrents',
             'isStalled': False, 'isPrivate': False, 'status': 4, 'percentDone': 0.95,
             'peersConnected': 1, 'rateUpload': 137e3, 'rateDownload': 0, 'downloadedEver': 0}),
    Torrent({'id': 4, 'name': 'FooF', 'downloadDir': '/completely/different/path/to/torrents',
             'isStalled': True, 'isPrivate': True, 'status': 0, 'percentDone': 0.48,
             'peersConnected': 0, 'rateUpload': 0, 'rateDownload': 0, 'downloadedEver': 583239}),
)


def getids(torrents, *ids):
    return set(t['id'] for t in torrents)



class Test_TorrentFilter(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(str(_TorrentFilter()), 'all')
        self.assertEqual(str(_TorrentFilter('*')), 'all')
        self.assertEqual(str(_TorrentFilter('idle')), 'idle')
        self.assertEqual(str(_TorrentFilter('!idle')), '!idle')
        self.assertEqual(str(_TorrentFilter('foo')), '~foo')
        self.assertEqual(str(_TorrentFilter('~foo')), '~foo')
        self.assertEqual(str(_TorrentFilter('=foo')), '=foo')
        self.assertEqual(str(_TorrentFilter('!=foo')), '!=foo')
        self.assertEqual(str(_TorrentFilter('name= foo')), '= foo')
        self.assertEqual(str(_TorrentFilter('name!=foo ')), '!=foo ')
        self.assertEqual(str(_TorrentFilter('%downloaded>17.2')), '%downloaded>17.2')

        with self.assertRaises(ValueError) as cm:
            _TorrentFilter('=')
        self.assertEqual(str(cm.exception), "Missing value: = ...")
        with self.assertRaises(ValueError) as cm:
            _TorrentFilter('%downloaded!>')
        self.assertEqual(str(cm.exception), "Missing value: %downloaded!> ...")
        # with self.assertRaises(ValueError) as cm:
        #     _TorrentFilter('tracker')
        # self.assertEqual(str(cm.exception), "Missing operator and value: tracker [<|<=|=|>|>=|~] ...")
        with self.assertRaises(ValueError) as cm:
            _TorrentFilter('name! =foo')
        self.assertEqual(str(cm.exception), "Malformed filter expression: 'name! =foo'")

    def test_parsing_spaces(self):
       self.assertEqual(str(_TorrentFilter(' idle ')), 'idle')
       self.assertEqual(str(_TorrentFilter('   %downloaded   ')), '%downloaded')
       self.assertEqual(str(_TorrentFilter(' name = foo')), '=foo')
       self.assertEqual(str(_TorrentFilter(' name != foo  ')), '!=foo')
       self.assertEqual(str(_TorrentFilter(' name= foo, bar and baz  ')), '= foo, bar and baz  ')

       self.assertEqual(str(_TorrentFilter(' =   foo, bar and baz ')), '=foo, bar and baz')
       self.assertEqual(str(_TorrentFilter('=   foo, bar and baz ')), '=   foo, bar and baz ')

    def test_unknown_filter(self):
        with self.assertRaises(ValueError) as cm:
            _TorrentFilter('foo=bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")
        with self.assertRaises(ValueError) as cm:
            _TorrentFilter('foo!~bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")

    def test_equality(self):
        self.assertEqual(_TorrentFilter('name=foo'), _TorrentFilter('name=foo'))
        self.assertNotEqual(_TorrentFilter('name=foo'), _TorrentFilter('name=Foo'))
        self.assertEqual(_TorrentFilter('complete'), _TorrentFilter('complete'))
        self.assertNotEqual(_TorrentFilter('complete'), _TorrentFilter('!complete'))
        self.assertEqual(_TorrentFilter('!private'), _TorrentFilter('!private'))
        self.assertNotEqual(_TorrentFilter('private'), _TorrentFilter('!private'))

    def test_equals_operator(self):
        tids = _TorrentFilter('name=Foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,})
        tids = _TorrentFilter('name=foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,})
        tids = _TorrentFilter('name=Foof').apply(tlist, ids=True)
        self.assertEqual(set(tids), set())
        tids = _TorrentFilter('name=FooF').apply(tlist, ids=True)
        self.assertEqual(set(tids), {4,})
        tids = _TorrentFilter('name=42').apply(tlist, ids=True)
        self.assertEqual(set(tids), set())

    def test_contains_operator(self):
        tids = _TorrentFilter('name~i').apply(tlist, ids=True)
        self.assertEqual(set(tids), {3,})
        tids = _TorrentFilter('name~oof').apply(tlist, ids=True)
        self.assertEqual(set(tids), {4,})
        tids = _TorrentFilter('name~oof').apply(tlist, ids=True)
        self.assertEqual(set(tids), {4,})
        tids = _TorrentFilter('name~OOF').apply(tlist, ids=True)
        self.assertEqual(set(tids), set())
        tids = _TorrentFilter('name~123').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,})

    def test_inverter(self):
        tids = _TorrentFilter('downloading').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,})
        tids = _TorrentFilter('!downloading').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3, 4})
        tids = _TorrentFilter('name~foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 4})
        tids = _TorrentFilter('name!~foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2, 3})
        tids = _TorrentFilter('!name~foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2, 3})
        tids = _TorrentFilter('!name!~foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 4})

    def test_invalid_operators(self):
        with self.assertRaises(ValueError) as cm:
            tuple(_TorrentFilter('%downloaded~4').apply(tlist, ids=True))
        self.assertEqual(str(cm.exception), "Invalid operator for filter '%downloaded': ~")

    def test_invalid_values(self):
        with self.assertRaises(ValueError) as cm:
            tuple(_TorrentFilter('rate-down>foo').apply(tlist, ids=True))
        self.assertEqual(str(cm.exception), "Invalid value for filter 'rate-down': 'foo'")

    def test_aliases(self):
        tids1 = tuple(_TorrentFilter('verifying').apply(tlist, ids=True))
        tids2 = tuple(_TorrentFilter('checking').apply(tlist, ids=True))
        self.assertEqual(set(tids1), set(tids2))

    def test_no_filter(self):
        tids = _TorrentFilter().apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,2,3,4})

    def test_larger_smaller_operator(self):
        # 375Ki == 384k
        tids = _TorrentFilter('rate-down>375Ki').apply(tlist, ids=True)
        self.assertEqual(set(tids), set())
        tids = _TorrentFilter('rate-down<375 Ki').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3, 4})
        tids = _TorrentFilter('rate-down>=375 ki').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,})
        tids = _TorrentFilter('rate-down<=384K').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 2, 3, 4})

        tids = _TorrentFilter('%downloaded>0').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 2, 3, 4})
        tids = _TorrentFilter('%downloaded>20').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3, 4})
        tids = _TorrentFilter('%downloaded>90').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3})
        tids = _TorrentFilter('%downloaded<90').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2, 4})
        tids = _TorrentFilter('%downloaded<20').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,})

    def test_larger_smaller_operator_on_strings(self):
        tids = _TorrentFilter('name<4').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3})
        tids = _TorrentFilter('name<=4').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3, 4})
        tids = _TorrentFilter('name<fo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2, 3})
        tids = _TorrentFilter('name<=Foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 2, 3})

        tids = _TorrentFilter('name>3').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2, 4})
        tids = _TorrentFilter('name>=3').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 2, 3, 4})
        tids = _TorrentFilter('name>Bar123').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 3, 4})
        tids = _TorrentFilter('name>=Bar123').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1, 2, 3, 4})

    def test_boolean_fallback(self):
        tids = _TorrentFilter('downloaded').apply(tlist, ids=True)
        self.assertEqual(set(tids), {4,})
        tids = _TorrentFilter('!downloaded').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,2,3})
        tids = _TorrentFilter('name').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,2,3,4})

    def test_name_is_default(self):
        tids = _TorrentFilter('=foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,})
        tids = _TorrentFilter('!=foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,3,4})
        tids = _TorrentFilter('~foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,4})
        tids = _TorrentFilter('!~foo').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,3})
        tl = list(tlist)
        tl.append(Torrent({'id': 999, 'name': ''}))
        tids = _TorrentFilter('!').apply(tl, ids=True)
        self.assertEqual(set(tids), {999,})

    def test_progress_filter(self):
        tids = _TorrentFilter('complete').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,})
        tids = _TorrentFilter('!complete').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2, 3, 4})
        tids = _TorrentFilter('%downloaded=48').apply(tlist, ids=True)
        self.assertEqual(set(tids), {4,})

    def test_status_filter(self):
        tids = _TorrentFilter('stopped').apply(tlist, ids=True)
        self.assertEqual(set(tids), {4,})
        tids = _TorrentFilter('downloading').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,})
        tids = _TorrentFilter('uploading').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,3})
        tids = _TorrentFilter('active').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,3})

    def test_private_filter(self):
        tids = _TorrentFilter('public').apply(tlist, ids=True)
        self.assertEqual(set(tids), {1,3})
        tids = _TorrentFilter('private').apply(tlist, ids=True)
        self.assertEqual(set(tids), {2,4})


class TestTorrentFilter(unittest.TestCase):
    def test_parser(self):
        for s in ('&', '|', '&idle', '|idle'):
            with self.assertRaisesRegex(ValueError, "can't start with operator"):
                TorrentFilter(s)
        for s in ('idle&', 'idle|'):
            with self.assertRaisesRegex(ValueError, "can't end with operator"):
                TorrentFilter(s)
        for s in ('idle||private', 'idle&&private', 'idle&|private', 'idle|&private',
                  'idle||private&name~foo|name~bar', 'name~foo|name~bar&idle|&private|name~baz'):
            with self.assertRaisesRegex(ValueError, "Consecutive operators: 'idle[&|]{2}private'"):
                TorrentFilter(s)
        TorrentFilter()

    def test_sequence_argument(self):
        f1 = TorrentFilter(['foo', 'bar'])
        f2 = TorrentFilter('foo|bar')
        self.assertEqual(f1, f2)

    def test_no_filters(self):
        ftlist = TorrentFilter().apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2, 3, 4})

    def test_any_allfilter_means_no_filters(self):
        f = TorrentFilter('name~f|all&public')
        self.assertEqual(f._filterchains, ())

    def test_AND_operator(self):
        ftlist = TorrentFilter('name~f&public').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 3})

        ftlist = TorrentFilter('name~f&public&!complete').apply(tlist)
        self.assertEqual(getids(ftlist), {3})

        ftlist = TorrentFilter('name~f&!complete&private&stopped').apply(tlist)
        self.assertEqual(getids(ftlist), {4})

    def test_OR_operator(self):
        ftlist = TorrentFilter('name~f|public').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 3, 4})

        ftlist = TorrentFilter('name~f|public|!complete').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2, 3, 4})

        ftlist = TorrentFilter('%downloaded<30|%downloaded>90').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2, 3})

        ftlist = TorrentFilter('%downloaded<30|seeding').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2})

        ftlist = TorrentFilter('seeding|%downloaded<30 |'
                                'connections=1|path~/different/').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2, 3, 4})

    def test_AND_OR_operator(self):
        ftlist = TorrentFilter('!stopped&complete|name=foof').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 4})

        ftlist = TorrentFilter('name~foo|active&private').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2, 4})

        ftlist = TorrentFilter('name~f&seeding|!complete&downloading|'
                                'connections&!downloading|id=4').apply(tlist)
        self.assertEqual(getids(ftlist), {1, 2, 3, 4})

    def test_equality(self):
        self.assertEqual(TorrentFilter('idle&private'),
                         TorrentFilter('idle&private'))
        self.assertEqual(TorrentFilter('idle&private'),
                         TorrentFilter('private&idle'))
        self.assertEqual(TorrentFilter('idle|private'),
                         TorrentFilter('private|idle'))
        self.assertNotEqual(TorrentFilter('idle|private'),
                            TorrentFilter('idle&private'))
        self.assertEqual(TorrentFilter('idle|private&stopped'),
                         TorrentFilter('stopped&private|idle'))
        self.assertNotEqual(TorrentFilter('idle|private&stopped'),
                            TorrentFilter('private|idle&stopped'))
        self.assertEqual(TorrentFilter('idle|private&stopped|name~foo'),
                         TorrentFilter('stopped&private|name~foo|idle'))
        self.assertNotEqual(TorrentFilter('idle|private&stopped|name~foo'),
                            TorrentFilter('stopped&private|idle'))
        self.assertEqual(TorrentFilter('idle&active|private&stopped|name~foo'),
                         TorrentFilter('stopped&private|name~foo|idle&active'))
        self.assertNotEqual(TorrentFilter('idle&active|private&stopped|name~foo'),
                            TorrentFilter('stopped&private|name~foo|idle'))

    def test_multiple_implied_name_filters(self):
        self.assertEqual(str(TorrentFilter('foo|bar')), '~foo|~bar')

    def test_combining_filters(self):
        f1 = TorrentFilter('name=foo')
        f2 = TorrentFilter('active')
        f3 = f1+f2
        self.assertEqual(f3, TorrentFilter('name=foo|active'))

        f1 = TorrentFilter('name~foo&private|path~/other/')
        f2 = TorrentFilter('active&private|public&!complete')
        f3 = f1+f2
        self.assertEqual(str(f3), ('~foo&private|path~/other/|'
                                   'active&private|public&!complete'))

        f1 = TorrentFilter('public&active')
        f2 = TorrentFilter('active&public')
        self.assertEqual(str(f1+f2), 'public&active')
        f3 = TorrentFilter('complete')
        self.assertEqual(str(f1+f2+f3), 'public&active|complete')
        self.assertEqual(str(f3+f2+f1), 'complete|active&public')

    def test_combining_any_filter_with_all_is_all(self):
        f = TorrentFilter('active') + TorrentFilter('all')
        self.assertEqual(f, TorrentFilter('all'))

        f = TorrentFilter('active') + TorrentFilter('private')
        self.assertEqual(f, TorrentFilter('active|private'))

    def test_needed_keys(self):
        f1 = TorrentFilter('public')
        self.assertEqual(set(f1.needed_keys), set(['private']))
        f2 = TorrentFilter('complete')
        self.assertEqual(set((f1+f2).needed_keys), set(['private', '%downloaded']))
        f3 = TorrentFilter('!private|active')
        self.assertEqual(set((f1+f2+f3).needed_keys),
                         set(['private', '%downloaded', 'peers-connected', 'status']))
