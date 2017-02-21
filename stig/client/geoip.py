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

try:
    import GeoIP

except ImportError:
    GEOIP_AVAILABLE = False
    def country_code(addr):
        return '?'

else:
    GEOIP_AVAILABLE = True
    _geoip = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
    def country_code(addr):
        return _geoip.country_code_by_addr(addr) or '?'
