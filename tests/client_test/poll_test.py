from stig.client.poll import RequestPoller
from stig.client.errors import ConnectionError

import asynctest
import asyncio

import logging
log = logging.getLogger(__name__)


class TestRequestPoller(asynctest.ClockedTestCase):
    def setUp(self):
        self.mock_request_args = None
        self.mock_request_kwargs = None
        self.mock_request_calls = 0

    def make_poller(self, *args, **kwargs):
        rp = RequestPoller(*args, **kwargs)

        def raise_exc(exc):
            raise exc
        rp.on_error(raise_exc, autoremove=False)
        return rp

    async def mock_request(self, *args, **kwargs):
        self.mock_request_args = args
        self.mock_request_kwargs = kwargs
        self.mock_request_calls += 1
        return self.mock_request_calls

    async def test_start_stop(self):
        rp = self.make_poller(self.mock_request, loop=self.loop)
        self.assertEqual(rp.running, False)
        await rp.start()
        self.assertEqual(rp.running, True)
        await rp.start()
        self.assertEqual(rp.running, True)
        await rp.stop()
        self.assertEqual(rp.running, False)
        await rp.start()
        self.assertEqual(rp.running, True)
        await rp.stop()
        self.assertEqual(rp.running, False)
        await rp.stop()
        self.assertEqual(rp.running, False)

    async def test_request_args(self):
        rp = self.make_poller(self.mock_request, 1, 2, 3, foo='bar',
                              loop=self.loop)
        await rp.start()
        await self.advance(0)
        self.assertEqual(self.mock_request_args, (1, 2, 3))
        self.assertEqual(self.mock_request_kwargs, {'foo': 'bar'})
        await rp.stop()

    async def test_interval(self):
        rp = self.make_poller(self.mock_request, interval=10, loop=self.loop)
        self.assertEqual(rp.interval, 10)
        rp.interval = 5
        self.assertEqual(rp.interval, 5)
        await rp.start()
        await self.advance(0)
        self.assertEqual(self.mock_request_calls, 1)
        await self.advance(rp.interval*2)
        self.assertEqual(self.mock_request_calls, 3)
        await self.advance(rp.interval*3)
        self.assertEqual(self.mock_request_calls, 6)
        await rp.stop()

    async def test_callbacks(self):
        rp = self.make_poller(self.mock_request, loop=self.loop)
        status = None
        def cb1(calls):
            nonlocal status
            if calls is None:
                status = None
            elif calls % 2 == 0:
                status = 'Even number of calls: %d' % calls

        def cb2(calls):
            nonlocal status
            if calls is None:
                status = None
            elif calls % 2 != 0:
                status = 'Uneven number of calls: %d' % calls

        rp.on_response(cb1)
        await rp.start()
        await self.advance(0)
        self.assertEqual(status, None)
        await self.advance(rp.interval)
        self.assertEqual(status, 'Even number of calls: 2')
        await self.advance(rp.interval)
        self.assertEqual(status, 'Even number of calls: 2')
        await self.advance(rp.interval)
        self.assertEqual(status, 'Even number of calls: 4')

        rp.on_response(cb2)
        await self.advance(rp.interval)
        self.assertEqual(status, 'Uneven number of calls: 5')
        await self.advance(rp.interval)
        self.assertEqual(status, 'Even number of calls: 6')
        await self.advance(rp.interval)
        self.assertEqual(status, 'Uneven number of calls: 7')

        await rp.stop()

    async def test_callback_gets_None_when_stopped(self):
        rp = self.make_poller(self.mock_request, loop=self.loop)
        status = None
        def cb(calls):
            nonlocal status
            status = '%s calls' % calls

        rp.on_response(cb)
        await rp.start()
        await self.advance(0)
        self.assertEqual(status, '1 calls')
        await self.advance(rp.interval)
        self.assertEqual(status, '2 calls')

        await rp.stop()
        await self.advance(0)
        self.assertEqual(status, 'None calls')

    async def test_request_raises_ConnectionError(self):
        # Connection fails after a few successfull requests
        requests_before_failure = 3
        requests_before_different_failure = 6
        requests = 0
        async def mock_request():
            nonlocal requests
            requests += 1
            if requests > requests_before_different_failure:
                raise ConnectionError('Another error')
            elif requests > requests_before_failure:
                raise ConnectionError('Server unreachable')
            else:
                return requests
        rp = RequestPoller(mock_request, loop=self.loop)

        # Collect responses
        responses = []
        def handle_response(response):
            if response is None:
                responses.append('no response')
            else:
                responses.append('response #%d' % response)
        rp.on_response(handle_response)

        # Collect exceptions
        errors = []
        def handle_error(exc):
            errors.append(exc)
        rp.on_error(handle_error)

        await rp.start()
        await self.advance(rp.interval * (requests_before_failure+5))
        self.assertEqual(rp.running, True)
        self.assertEqual(len(responses), 9)
        self.assertEqual(responses, ['response #1',
                                     'response #2',
                                     'response #3',
                                     'no response',
                                     'no response',
                                     'no response',
                                     'no response',
                                     'no response',
                                     'no response'])
        self.assertEqual(len(errors), 2)
        self.assertIsInstance(errors[0], ConnectionError)
        self.assertEqual(str(errors[0]), 'Connection failed: Server unreachable')
        self.assertIsInstance(errors[1], ConnectionError)
        self.assertEqual(str(errors[1]), 'Connection failed: Another error')

        await rp.stop()

    async def test_changing_request(self):
        status = []
        async def request1():
            status.append('{}: request1() called'.format(self.loop.time()))
        async def request2(a, b):
            status.append('{}: request2({}, {}) called'.format(self.loop.time(), a, b))

        rp = self.make_poller(request1, loop=self.loop)
        await rp.start()
        await self.advance(0)
        self.assertEqual(status, ['%d: request1() called' % 0])

        # Setting the request restarts the internal polling loop and resets
        # loop.time() to 0 for some reason.
        rp.set_request(request2, 'one', 2)
        await self.advance(rp.interval * 3)
        self.assertEqual(status, ['%d: request1() called' % 0,
                                  '%d: request2(one, 2) called' % (rp.interval*1),
                                  '%d: request2(one, 2) called' % (rp.interval*2),
                                  '%d: request2(one, 2) called' % (rp.interval*3)])
        await rp.stop()

    async def test_manual_polling(self):
        rp = self.make_poller(self.mock_request, loop=self.loop)
        await rp.start()
        self.assertEqual(self.mock_request_calls, 0)
        await self.advance(0)
        self.assertEqual(self.mock_request_calls, 1)
        rp.poll()
        await self.advance(0)
        self.assertEqual(self.mock_request_calls, 2)
        rp.poll()
        await self.advance(0)
        self.assertEqual(self.mock_request_calls, 3)
        await rp.stop()
