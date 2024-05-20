# Load __version__ variable without importing the whole stig module
import re

from setuptools import find_packages, setup

version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]",
                          open('stig/__init__.py').read(), re.M)
if version_match:
    __version__ = version_match.group(1)
else:
    raise RuntimeError("Unable to find __version__")

setup(
    name             = 'stig',
    version          = __version__,
    license          = 'GPLv3+',
    author           = 'Random User',
    author_email     = 'rndusr@posteo.de',

    description      = 'TUI and CLI client for the Transmission daemon',
    long_description = (
        "There is no `long_description` because PyPI doesn't support org-mode "
        "conversion with `pandoc` is wonky and I can't be arsed to convert "
        "the README by hand."
        "\n\n"
        "Please read the README in the [repo](https://github.com/rndusr/stig)."
    ),
    long_description_content_type='text/markdown',

    url              = 'https://github.com/rndusr/stig',
    keywords         = 'bittorrent torrent transmission',

    packages         = find_packages(),
    package_data     = {'stig': ['settings/default.theme']},

    python_requires  = '>=3.6',
    install_requires = [
        'urwid>=2.6.12',
        'urwidtrees==1.0.3',
        'aiohttp==3.*',
        'async_timeout',
        'pyxdg',
        'blinker',
        'natsort',
    ],
    extras_require = {
        'setproctitle': ['setproctitle'],
        'proxy': ['aiohttp-socks'],
    },
    tests_require = [
        'pytest>=5,<6',
        'asynctest>=0.11',
    ],

    entry_points = { 'console_scripts': [ 'stig = stig:run' ] },

    classifiers = [
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Environment :: Console',
        'Operating System :: Unix',
        'Development Status :: 3 - Alpha',
    ],
)
