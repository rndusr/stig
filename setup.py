# TODO: https://packaging.python.org/

with open('stig/version.py') as f:
    exec(f.read())  # Load __version__ into globals()

from setuptools import setup, find_packages

setup(
    name = 'stig',
    version = __version__,
    license = 'GPLv3+',
    author_email = 'rndusr@posteo.de',
    description = 'TUI and CLI client for the Transmission daemon',
    url = 'https://github.com/rndusr/stig',
    keywords = 'bittorrent torrent transmission',

    packages = find_packages(),
    package_data={'stig': ['settings/default.theme']},

    install_requires = [
        'urwid>=1.3.0',
        'aiohttp>=0.22.5',
        'appdirs',
        'blinker',
    ],

    entry_points = { 'console_scripts': [ 'stig = stig:run' ] },

    classifiers = [
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.5',
        'Environment :: Console',
        'Operating System :: Unix',
    ],
)
