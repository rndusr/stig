# Create long_description from README.org if possible
long_description = ''
try:
    import pypandoc
    import os
    if os.path.exists('README.org'):
        long_description = pypandoc.convert('README.org', 'rst')
        import restructuredtext_lint as rst
        rst.lint(long_description)
except ImportError:
    pass

# Load __version__ variable without importing the whole stig module
with open('stig/__version__.py') as f:
    exec(f.read())

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

    python_requires  = '>=3.5',
    install_requires = [
        'urwid>=2.0',
        'urwidtrees>=1.0.3dev0',
        'aiohttp>=3',
        'async_timeout',
        'pyxdg',
        'blinker',
        'natsort',
    ],
    extras_require = {
        'geoip': ['maxminddb'],
        'setproctitle': ['setproctitle'],
    },
    tests_require = [
        'asynctest>=0.11',
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
