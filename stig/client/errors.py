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


class ClientError(Exception):
    prefix = ''
    def __init__(self, message, *args, **kwargs):
        super().__init__(self.prefix + str(message))

    def __eq__(self, other):
        return type(self) == type(other) and self.args == other.args

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(type(self).__name__ + str(self))

class ConnectionError(ClientError):
    prefix = 'Connection failed: '

class RPCError(ClientError):
    prefix = 'Invalid RPC request: '

class AuthError(ClientError):
    prefix = 'Authentication failed: '

class URLParserError(ClientError, ValueError):
    prefix = 'Invalid URL: '
