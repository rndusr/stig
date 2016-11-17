from tctrl.client.aiotransmission.rpc import TransmissionURL

import unittest


class TestTransmissionURL(unittest.TestCase):
    def test_default(self):
        url = TransmissionURL()
        self.assertNotEqual(url.scheme, None)
        self.assertNotEqual(url.hostname, None)
        self.assertNotEqual(url.port, None)

    def test_attributes(self):
        url = TransmissionURL('http://localhost:123')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.hostname, 'localhost')
        self.assertEqual(url.port, 123)

    def test_authenticaion(self):
        url = TransmissionURL('https://foo:bar@localhost:123')
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.hostname, 'localhost')
        self.assertEqual(url.port, 123)
        self.assertEqual(url.username, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_no_scheme(self):
        url = TransmissionURL('foohost')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.hostname, 'foohost')
        self.assertEqual(url.port, 9091)

    def test_no_scheme_with_port(self):
        url = TransmissionURL('foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.hostname, 'foohost')
        self.assertEqual(url.port, 9999)

    def test_no_scheme_user_and_pw(self):
        url = TransmissionURL('foo:bar@foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.hostname, 'foohost')
        self.assertEqual(url.port, 9999)
        self.assertEqual(url.username, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_str(self):
        url = TransmissionURL('https://foo:bar@localhost:123')
        self.assertEqual(str(url), 'https://foo@localhost:123')
        url = TransmissionURL('localhost')
        self.assertEqual(str(url), 'localhost')

    def test_repr(self):
        url = TransmissionURL('https://foo:bar@localhost:123')
        self.assertEqual(repr(url), 'https://foo:bar@localhost:123/transmission/rpc')
