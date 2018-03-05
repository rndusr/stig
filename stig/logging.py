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

import logging
import sys

MAIN_PACKAGE_NAME = __name__[:__name__.index('.')]

def make_logger(modname=None):
    if modname is None:
        # Default logger, for which debugging is always enabled if it is for
        # any other modules
        return logging.getLogger(MAIN_PACKAGE_NAME)
    elif modname.startswith(MAIN_PACKAGE_NAME+'.'):
        # Remove main package name from logger name ('foo.bar.baz' -> 'bar.baz')
        loggername = modname[len(MAIN_PACKAGE_NAME)+1:]
    else:
        loggername = modname
    return logging.getLogger(loggername)

log = make_logger()


def setup(debugmods, filepath=None):
    class PerLevelFormatter(logging.Formatter):
        """Use different formatter per level"""
        datefmt = '%H:%M:%S'
        formatters = {
            logging.DEBUG: logging.Formatter('%(asctime)s.%(msecs)03d: [%(name)s] %(message)s', datefmt=datefmt),
        }
        default_fmtr = logging.Formatter('%(message)s', datefmt=datefmt)

        def format(self, record):
            fmtr = self.formatters.get(record.levelno, self.default_fmtr)
            return fmtr.format(record)

    root_logger = logging.getLogger()
    formatter = PerLevelFormatter()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(logging.INFO)

    if debugmods:
        # Enable debugging for default logger
        logging.getLogger(MAIN_PACKAGE_NAME).setLevel(logging.DEBUG)

        modnames = debugmods
        for modname in modnames:
            logging.getLogger(modname).setLevel(logging.DEBUG)
            log.debug('Debugging messages enabled: ' + modname)

    if filepath is not None:
        file_handler = logging.FileHandler(filepath)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        log.debug('Logging to file: %r', file_handler.baseFilename)


def redirect_level(level, stream=sys.stderr):
    root_logger = logging.getLogger()

    # Add filters to all existing handlers to NOT log the specified level
    for h in root_logger.handlers:
        h.addFilter(lambda record: record.levelname != level)

    # Add new handler that only logs the specified level
    lvlhandler = logging.StreamHandler(stream)
    lvlhandler.addFilter(lambda record: record.levelname == level)
    root_logger.addHandler(lvlhandler)


def start_profiling(func, filepath, statistical=True):
    import pprofile
    if statistical:
        prof = pprofile.StatisticalProfile()
    else:
        prof = pprofile.Profile()

    def stop_profiling(prof, filepath):
        print('Writing profiling data: %s' % filepath, file=sys.stderr)
        print('You can use kcachegrind to analyze it.', file=sys.stderr)
        with open(filepath, 'w') as f:
            prof.callgrind(f)

    # This makes the `finally` block work as expected if we're terminated by
    # SIGTERM, which happens by default when running `timeout 30 stig ...`.
    # https://stackoverflow.com/a/42200623
    # https://mail.python.org/pipermail/python-ideas/2016-February/038474.html
    import signal
    class SigTerm(SystemExit): pass
    def sigterm(sig, frame): raise SigTerm
    signal.signal(15, sigterm)

    try:
        with prof():
            func()
    finally:
        stop_profiling(prof, filepath)
