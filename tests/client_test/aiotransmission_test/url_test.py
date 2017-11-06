from stig.client.aiotransmission.rpc import (TransmissionURL, URLParserError)

import unittest


class TestTransmissionURL(unittest.TestCase):
    def test_default(self):
        url = TransmissionURL()
        self.assertNotEqual(url.scheme, None)
        self.assertNotEqual(url.host, None)
        self.assertNotEqual(url.port, None)

    def test_attributes(self):
        url = TransmissionURL('http://localhost:123')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 123)

    def test_authentication(self):
        url = TransmissionURL('https://foo:bar@localhost:123')
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 123)
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_authentication_empty_password(self):
        url = TransmissionURL('foo:@localhost')
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_authentication_empty_user(self):
        url = TransmissionURL(':bar@localhost')
        self.assertEqual(url.user, None)
        self.assertEqual(url.password, 'bar')
        self.assertEqual(url.host, 'localhost')

    def test_authentication_empty_user_and_password(self):
        url = TransmissionURL(':@localhost')
        self.assertEqual(url.user, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_no_scheme(self):
        url = TransmissionURL('foohost')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9091)

    def test_no_scheme_with_port(self):
        url = TransmissionURL('foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9999)

    def test_no_scheme_user_and_pw(self):
        url = TransmissionURL('foo:bar@foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9999)
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_str(self):
        url = TransmissionURL('https://foo:bar@localhost:123')
        self.assertEqual(str(url), 'https://foo:bar@localhost:123/transmission/rpc')
        url = TransmissionURL('localhost')
        self.assertEqual(str(url), 'http://localhost:9091/transmission/rpc')

    def test_repr(self):
        url = TransmissionURL('https://foo:bar@localhost:123')
        self.assertEqual(repr(url), '<TransmissionURL https://foo:bar@localhost:123/transmission/rpc>')

    def test_mutability_and_cache(self):
        url = TransmissionURL('https://foo.example.com:123/foo')
        url.port = 321
        url.host = 'bar.example.com'
        url.scheme = 'http'
        self.assertEqual(str(url), 'http://bar.example.com:321/foo')

        self.assertEqual(url.domain, 'example.com')
        url.host = 'foo.bar.com'
        self.assertEqual(url.domain, 'bar.com')
        self.assertEqual(str(url), 'http://foo.bar.com:321/foo')
