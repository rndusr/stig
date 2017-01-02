with open('stig/version.py') as f:
    exec(f.read())  # Load __version__ into globals()

# Convert README.org to rst for pypi page
try:
    import pypandoc
    import re

    long_description = []
    imgref_regex = re.compile(r'^\s*\|image\d+\|')
    for line in pypandoc.convert('README.org', 'rst').split('\n'):
        if not imgref_regex.match(line):
            long_description.append(line)
    long_description = '\n'.join(long_description)

except ImportError:
    long_description = ''


from setuptools import setup, find_packages
setup(
    name = 'stig',
    version = __version__,
    license = 'GPLv3+',
    author = 'Random User',
    author_email = 'rndusr@posteo.de',

    description = 'TUI and CLI client for the Transmission daemon',
    long_description = long_description,

    url = 'https://github.com/rndusr/stig',
    keywords = 'bittorrent torrent transmission',

    packages = find_packages(),
    package_data={'stig': ['settings/default.theme']},

    install_requires = [
        'urwid>=1.3.0',
        'aiohttp>=0.22.5',
        'urwidtrees>=1.0.1.1',
        'appdirs',
        'blinker',
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
