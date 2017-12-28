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

from .__version__ import __version__
__appname__ = __name__.split('.')[0]
__url__ = 'https://github.com/rndusr/stig'

def run():
    try:
        from . import main
        if main.cliargs['profile_file'] is not None:
            main.logging.start_profiling(main.run,
                                         filepath=main.cliargs['profile_file'],
                                         statistical=False)
        else:
            main.run()
    except KeyboardInterrupt:
        pass
