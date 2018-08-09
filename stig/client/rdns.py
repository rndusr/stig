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

from ..logging import make_logger
log = make_logger(__name__)

import socket
import concurrent

_cache = {}
_lookup_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100)


def gethostbyaddr(ip):
    hostname = _cache.get(ip)
    if hostname is None:
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except OSError:
            hostname = ip
        finally:
            _cache[ip] = hostname
    return hostname


def gethostbyaddr_from_cache(ip):
    return _cache.get(ip)


def query(*ips, callback=None):
    def cb(fut):
        hostname = fut.result()
        if callback:
            callback(hostname)

    for ip in ips:
        fut = _lookup_pool.submit(gethostbyaddr, ip)
        fut.add_done_callback(cb)
