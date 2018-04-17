from stig.client.filters.torrent import (SingleTorrentFilter, TorrentFilter)
from stig.client.aiotransmission.torrent import Torrent

import unittest


tlist = (
    Torrent({'id': 1, 'name': 'Foo', 'downloadDir': '/some/path/to/torrents',
             'isPrivate': False, 'status': 6, 'percentDone': 1, 'eta': -1,
             'peersConnected': 0, 'rateUpload': 0, 'rateDownload': 0, 'downloadedEver': 0,
             'metadataPercentComplete': 1, 'trackerStats': []}),
    Torrent({'id': 2, 'name': 'Bar123', 'downloadDir': '/some/path/to/torrents/',
             'isPrivate': True, 'status': 4, 'percentDone': 0.0235, 'eta': 84600,
             'peersConnected': 3, 'rateUpload': 58e3, 'rateDownload': 384e3, 'downloadedEver': 0,
             'metadataPercentComplete': 1, 'trackerStats': []}),
    Torrent({'id': 3, 'name': 'Fim', 'downloadDir': '/other/path/to/torrents',
             'isPrivate': False, 'status': 4, 'percentDone': 0.95, 'eta': 3600,
             'peersConnected': 1, 'rateUpload': 137e3, 'rateDownload': 0, 'downloadedEver': 0,
             'metadataPercentComplete': 1, 'trackerStats': []}),
    Torrent({'id': 4, 'name': 'FooF', 'downloadDir': '/completely/different/path/to/torrents',
             'isPrivate': True, 'status': 0, 'percentDone': 0.48, 'eta': -2,
             'peersConnected': 0, 'rateUpload': 0, 'rateDownload': 0, 'downloadedEver': 583239,
             'metadataPercentComplete': 1, 'trackerStats': []}),
)


def getids(torrents, *ids):
    return set(t['id'] for t in torrents)



class TestSingleTorrentFilter(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(str(SingleTorrentFilter()), 'all')
        self.assertEqual(str(SingleTorrentFilter('*')), 'all')
        self.assertEqual(str(SingleTorrentFilter('idle')), 'idle')
        self.assertEqual(str(SingleTorrentFilter('!idle')), '!idle')
        self.assertEqual(str(SingleTorrentFilter('foo')), '~foo')
        self.assertEqual(str(SingleTorrentFilter('~foo')), '~foo')
        self.assertEqual(str(SingleTorrentFilter('=foo')), '=foo')
        self.assertEqual(str(SingleTorrentFilter('!=foo')), '!=foo')
        self.assertEqual(str(SingleTorrentFilter('name= foo')), "=' foo'")
        self.assertEqual(str(SingleTorrentFilter('name!=foo ')), "!='foo '")
        self.assertEqual(str(SingleTorrentFilter('%downloaded>17.2')), '%downloaded>17.2%')

        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('=')
        self.assertEqual(str(cm.exception), "Missing value: = ...")
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('%downloaded!>')
        self.assertEqual(str(cm.exception), "Missing value: %downloaded!> ...")
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('name! =foo')
        self.assertEqual(str(cm.exception), "Malformed filter expression: 'name! =foo'")

    def test_parsing_spaces(self):
        self.assertEqual(str(SingleTorrentFilter(' idle ')), 'idle')
        self.assertEqual(str(SingleTorrentFilter('   %downloaded   ')), '%downloaded')
        self.assertEqual(str(SingleTorrentFilter(' name = foo')), '=foo')
        self.assertEqual(str(SingleTorrentFilter(' name != foo  ')), '!=foo')
        self.assertEqual(str(SingleTorrentFilter(' name= foo, bar and baz  ')), "=' foo, bar and baz  '")

        self.assertEqual(str(SingleTorrentFilter(' =   foo, bar and baz ')), '=foo, bar and baz')
        self.assertEqual(str(SingleTorrentFilter('=   foo, bar and baz ')), "='   foo, bar and baz '")

    def test_unknown_filter(self):
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('foo=bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")
        with self.assertRaises(ValueError) as cm:
            SingleTorrentFilter('foo!~bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")

    def test_equality(self):
        self.assertEqual(SingleTorrentFilter('name=foo'), SingleTorrentFilter('name=foo'))
        self.assertNotEqual(SingleTorrentFilter('name=foo'), SingleTorrentFilter('name=Foo'))
        self.assertEqual(SingleTorrentFilter('complete'), SingleTorrentFilter('complete'))
        self.assertNotEqual(SingleTorrentFilter('complete'), SingleTorrentFilter('!complete'))
        self.assertEqual(SingleTorrentFilter('!private'), SingleTorrentFilter('!private'))
        self.assertNotEqual(SingleTorrentFilter('private'), SingleTorrentFilter('!private'))

    def test_equals_operator(self):
        tids = SingleTorrentFilter('name=Foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,})
        tids = SingleTorrentFilter('name=foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,})
        tids = SingleTorrentFilter('name=Foof').apply(tlist, key='id')
        self.assertEqual(set(tids), set())
        tids = SingleTorrentFilter('name=FooF').apply(tlist, key='id')
        self.assertEqual(set(tids), {4,})
        tids = SingleTorrentFilter('name=42').apply(tlist, key='id')
        self.assertEqual(set(tids), set())

    def test_contains_operator(self):
        tids = SingleTorrentFilter('name~i').apply(tlist, key='id')
        self.assertEqual(set(tids), {3,})
        tids = SingleTorrentFilter('name~oof').apply(tlist, key='id')
        self.assertEqual(set(tids), {4,})
        tids = SingleTorrentFilter('name~oof').apply(tlist, key='id')
        self.assertEqual(set(tids), {4,})
        tids = SingleTorrentFilter('name~OOF').apply(tlist, key='id')
        self.assertEqual(set(tids), set())
        tids = SingleTorrentFilter('name~123').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,})

    def test_inverter(self):
        tids = SingleTorrentFilter('downloading').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,})
        tids = SingleTorrentFilter('!downloading').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3, 4})
        tids = SingleTorrentFilter('name~foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 4})
        tids = SingleTorrentFilter('name!~foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3})
        tids = SingleTorrentFilter('!name~foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3})
        tids = SingleTorrentFilter('!name!~foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 4})

    def test_invalid_operators(self):
        with self.assertRaises(ValueError) as cm:
            tuple(SingleTorrentFilter('%downloaded~4').apply(tlist, key='id'))
        self.assertEqual(str(cm.exception), "Invalid operator for filter '%downloaded': ~")

    def test_invalid_values(self):
        with self.assertRaises(ValueError) as cm:
            tuple(SingleTorrentFilter('rate-down>foo').apply(tlist, key='id'))
        self.assertEqual(str(cm.exception), "Invalid value for filter 'rate-down': 'foo'")

    def test_aliases(self):
        tids1 = tuple(SingleTorrentFilter('verifying').apply(tlist, key='id'))
        tids2 = tuple(SingleTorrentFilter('checking').apply(tlist, key='id'))
        self.assertEqual(set(tids1), set(tids2))

    def test_no_filter(self):
        tids = SingleTorrentFilter().apply(tlist, key='id')
        self.assertEqual(set(tids), {1,2,3,4})

    def test_larger_smaller_operator(self):
        # 375Ki == 384k
        tids = SingleTorrentFilter('rate-down>375Ki').apply(tlist, key='id')
        self.assertEqual(set(tids), set())
        tids = SingleTorrentFilter('rate-down<375 Ki').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3, 4})
        tids = SingleTorrentFilter('rate-down>=375 ki').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,})
        tids = SingleTorrentFilter('rate-down<=384K').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 2, 3, 4})

        tids = SingleTorrentFilter('%downloaded>0').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 2, 3, 4})
        tids = SingleTorrentFilter('%downloaded>20').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3, 4})
        tids = SingleTorrentFilter('%downloaded>90').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3})
        tids = SingleTorrentFilter('%downloaded<90').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 4})
        tids = SingleTorrentFilter('%downloaded<20').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,})

    def test_larger_smaller_operator_on_strings(self):
        tids = SingleTorrentFilter('name<4').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3})
        tids = SingleTorrentFilter('name<=4').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3, 4})
        tids = SingleTorrentFilter('name<fo').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3})
        tids = SingleTorrentFilter('name<=Foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 2, 3})

        tids = SingleTorrentFilter('name>3').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 4})
        tids = SingleTorrentFilter('name>=3').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 2, 3, 4})
        tids = SingleTorrentFilter('name>Bar123').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3, 4})
        tids = SingleTorrentFilter('name>=Bar123').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 2, 3, 4})

    def test_boolean_fallback(self):
        tids = SingleTorrentFilter('downloaded').apply(tlist, key='id')
        self.assertEqual(set(tids), {4,})
        tids = SingleTorrentFilter('!downloaded').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,2,3})
        tids = SingleTorrentFilter('name').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,2,3,4})

    def test_name_is_default(self):
        tids = SingleTorrentFilter('=foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,})
        tids = SingleTorrentFilter('!=foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,3,4})
        tids = SingleTorrentFilter('~foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,4})
        tids = SingleTorrentFilter('!~foo').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,3})
        tl = list(tlist)
        tl.append(Torrent({'id': 999, 'name': ''}))
        tids = SingleTorrentFilter('!').apply(tl, key='id')
        self.assertEqual(set(tids), {999,})

    def test_progress_filter(self):
        tids = SingleTorrentFilter('complete').apply(tlist, key='id')
        self.assertEqual(set(tids), {1,})
        tids = SingleTorrentFilter('!complete').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3, 4})
        tids = SingleTorrentFilter('%downloaded=48').apply(tlist, key='id')
        self.assertEqual(set(tids), {4,})

    def test_status_filter(self):
        tids = SingleTorrentFilter('stopped').apply(tlist, key='id')
        self.assertEqual(set(tids), {4,})
        tids = SingleTorrentFilter('downloading').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,})
        tids = SingleTorrentFilter('uploading').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3})
        tids = SingleTorrentFilter('active').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3})

    def test_private_filter(self):
        tids = SingleTorrentFilter('public').apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 3})
        tids = SingleTorrentFilter('private').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 4})

    def test_path_filter(self):
        f = SingleTorrentFilter('path=/some/path/to/torrents/')
        self.assertEqual(f, SingleTorrentFilter('path=/some/path/to/torrents'))
        tids = f.apply(tlist, key='id')
        self.assertEqual(set(tids), {1, 2})

    def test_eta_filter_larger_smaller(self):
        tids = SingleTorrentFilter('eta>1h').apply(tlist, key='id')
        self.assertEqual(set(tids), {2,})
        tids = SingleTorrentFilter('eta>=1h').apply(tlist, key='id')
        self.assertEqual(set(tids), {2, 3})


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

        f1 = TorrentFilter('name~foo&private|path~other')
        f2 = TorrentFilter('active&private|public&!complete')
        f3 = f1+f2
        self.assertEqual(str(f3), ('~foo&private|path~other|'
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
