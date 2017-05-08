# Create long_description from README.org if possible
long_description = ''
try:
    import pypandoc
    import os
    if os.path.exists('README.org'):
        long_description = pypandoc.convert('README.org', 'rst')
except ImportError:
    pass


with open('stig/version.py') as f:
    exec(f.read())  # Load __version__ into globals()

from setuptools import setup, find_packages
setup(
    name             = 'stig',
    version          = __version__,
    license          = 'GPLv3+',
    author           = 'Random User',
    author_email     = 'rndusr@posteo.de',

    description      = 'TUI and CLI client for the Transmission daemon',
    long_description = long_description,

    url              = 'https://github.com/rndusr/stig',
    keywords         = 'bittorrent torrent transmission',

    packages         = find_packages(),
    package_data     = {'stig': ['settings/default.theme']},

    install_requires = [
        'urwid>=1.3.0',
        'urwidtrees>=1.0.3dev0',
        'aiohttp>=0.22.5',
        'appdirs',
        'blinker',
        'natsort',
    ],

    entry_points = { 'console_scripts': [ 'stig = stig:run' ] },

    classifiers = [
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Environment :: Console',
        'Operating System :: Unix',
        'Development Status :: 3 - Alpha',
    ],
)
