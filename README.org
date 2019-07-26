* stig
  [[https://pypi.python.org/pypi/stig][file:https://img.shields.io/pypi/v/stig.svg]]
  [[file:https://img.shields.io/pypi/status/stig.svg]]
  [[file:https://img.shields.io/pypi/l/stig.svg]]
  [[file:https://img.shields.io/pypi/pyversions/stig.svg]]
  [[file:https://img.shields.io/github/last-commit/rndusr/stig.svg]]

  [[file:https://raw.githubusercontent.com/rndusr/stig/master/screenshot.png]]

  stig is a TUI (text user interface) and CLI (command line interface) client
  for the [[http://www.transmissionbt.com/][BitTorrent client Transmission]].

  stig being in alpha status does *not* mean you should expect bugs.  It's
  supposed to indicate that behaviour may change with a new release since I'm
  still experimenting with what works best.  If you know how to make stig more
  flexible, convenient, intuitive or just /better/, feel free to open an issue.

** Features
   - *Filters* are used to list/start/stop/remove/etc torrents matching any
     combination of criteria
   - *Tabs* with list of torrents/peers/files, documentation, etc
   - *Commands* or *sub-commands* (think git) do everything, and they can be
     invoked
     - through single- or multi-key (think emacs) *keybindings*,
     - by entering them in a *command prompt* (think vi),
     - by providing them as *CLI arguments* in your interactive shell or in
       *scripts*,
     - or by listing them in an *rc file*.
   - *Color themes* support 16 and 256 colors
   - *Complete built-in documentation* with ~help~ command or ~--help~ argument
   - Full *API abstraction layer* makes it possible to add support for other
     BitTorrent clients with RPC interfaces (contributors are welcome)

** Examples
   Add two torrents, one by file and one by hash, and exit
   #+BEGIN_SRC sh
   $ stig add /path/to/some.torrent d4d6b73851fe3288e40389a8e1fb98124a9b9ba5
   #+END_SRC

   Connect to non-default host and present the TUI
   #+BEGIN_SRC sh
   $ stig set connect.host torrents.local
   #+END_SRC

   Print all uploading and/or downloading torrents on localhost:9092 and exit
   #+BEGIN_SRC sh
   $ stig set connect.port 9092 \; ls active
   #+END_SRC

   List torrents with more than 50 seeds, then remove them
   #+BEGIN_SRC sh
   $ stig ls 'seeds>50'
   $ stig rm 'seeds>50'
   #+END_SRC

   Stop down/uploading torrents with ~/foo/~ in their download path and a ratio
   above 10
   #+BEGIN_SRC sh
   $ stig stop 'path~/foo/&ratio>10'
   #+END_SRC

   Open two tabs with different torrent lists:
     - slowly uploading torrents with ~/foo/~ in their download path
     - small or well-seeded torrents, sorted by size (ascending) and number of
       seeds (descending)
   #+BEGIN_SRC sh
   $ stig tab ls 'path~/foo/&rate-up<10k' \; tab ls 'size<500M|seeds>=1k' --sort 'size,!seeds'
   #+END_SRC

** Configuration and Scripting
   All configuration is done in an rc file, which is just a script containing a
   list of commands (think vim and .vimrc) that are executed during startup.
   The default rc file is ~$XDG_CONFIG_HOME/stig/rc~.  ~XDG_CONFIG_HOME~
   defaults to ~$HOME/.config~ if not set.  Because a default rc file is empty,
   it is not created automatically to avoid clutter.

   See ~stig help cfgman~ for more information.

*** Example rc file
   #+BEGIN_SRC
   # Host that runs Transmission daemon
   set connect.host example.org
   set connect.port 123

   # Update torrent/peer/file/etc lists every 10 seconds
   set tui.poll 10

   # Default columns in torrent lists
   set columns.torrents name ratio rate-up rate-down

   # Open a few tabs on startup
   tab ls active --sort !%downloaded,path,!rate
   tab ls paused --sort !%downloaded --columns name,%downloaded,ratio,size
   tab ls isolated --sort tracker --columns name,path
   #+END_SRC

   Run different rc files either with ~stig -c path/to/file~ or with the ~rc~
   command.  You can even turn them into executables with the shebang
   ~#!/path/to/stig -Tc~ (~-T~ disables the TUI, ~-c~ specifies the rc file).

*** Example maintenance script
   #+BEGIN_SRC
   #!/path/to/stig -Tc
   rm path=/path/to/torrents/trash
   pause seeds>100
   start seeds<20&size>10G|seeds<50&size>20G
   #+END_SRC

** Installation
   The [[https://pypi.python.org/pypi/stig][latest release]] is always on PyPI.

   For Arch Linux stig is available on AUR as [[https://aur.archlinux.org/packages/stig][stig]] and the latest development
   version as [[https://aur.archlinux.org/packages/stig-git][stig-git]].

*** Pipx (recommended)
    [[https://github.com/pipxproject/pipx][Pipx]] installs applications in self-contained virtual environments in
    ~$HOME/.local/pipx/~ that include all dependencies.  Executables are
    sym-linked to ~$HOME/.local/bin/~.

    #+BEGIN_SRC sh
    $ pipx install stig
    $ pipx upgrade stig
    $ pipx uninstall stig
    #+END_SRC

*** Pip
    [[https://pip.pypa.io/en/stable/][pip]] installs applications with their dependencies in the system-wide
    (~/usr/local~) or user-wide (~$HOME/.local~) environment.

    #+BEGIN_SRC sh
    $ pip3 install stig         # Installs in /usr/local/
    $ pip3 install --user stig  # Installs in $HOME/.local/
    #+END_SRC

    To update, add the ~--upgrade~ or ~-U~ option.

*** Extras
   The following extras are available to enable optional features:
     - ~geoip~ :: Display peers' country codes
     - ~setproctitle~ :: Strip arguments from process title when running in tmux
                         session (this requires Python headers; e.g.
                         ~apt-get install libpython3-dev~)

   To install depdencies for an extra, provide the ~--spec~ option to pipx.
   #+BEGIN_SRC sh
   $ pipx install stig --spec 'stig[geoip,setproctitle]'
   #+END_SRC

*** Development version
    To install the latest development version, use pipx's ~--spec~ option.
   #+BEGIN_SRC sh
   $ pipx install stig --spec 'git+https://github.com/rndusr/stig.git#egg=stig'
   #+END_SRC

*** Developing
    To make your code changes effective immediately, you can either run
    ~python3 -m stig <ARGUMENTS>~ in the project directory or use ~pip3~'s
    ~--editable~ option.

    To run the tests, simply run ~make test~ in the project directory.  This
    creates a virtual environment in ~./venv~, installs stig and its
    dependencies in there and runs all available tests.

    If you want to only run tests for a specific module or package:

    1. Create a virtual environment:
       ~make venv~
    2. Activate it:
       ~. venv/bin/activate~
    3. Pass any path in the ~tests~ directory to pytest:
       ~venv/bin/pytest tests/settings~

** Requirements
   - Python >=3.5
   - [[http://www.urwid.org/][urwid]] >=1.3.0
   - [[https://github.com/pazz/urwidtrees][urwidtrees]] >=1.0.3dev0
   - [[https://pypi.python.org/pypi/aiohttp][aiohttp]]
   - [[https://pypi.python.org/pypi/async_timeout][async_timeout]]
   - [[https://pypi.python.org/pypi/pyxdg][pyxdg]]
   - [[https://pypi.python.org/pypi/blinker][blinker]]
   - [[https://pypi.python.org/pypi/natsort][natsort]]
   - [[https://pypi.org/project/maxminddb/][maxminddb]] (optional; shows country codes in peer lists)
   - [[https://pypi.python.org/pypi/setproctitle/1.1.10][setproctitle]] (optional; prettifies the process name)
   - [[https://pypi.python.org/pypi/asynctest/][asynctest]] (only needed to run tests)

** Contributing
   Pull requests, bug reports, features requests, ideas for improvement and all
   other constructive contributions are welcome.

   If you want to contribute code and get stuck, don't know where to even begin,
   or just to make sure you're not duplicating someone else's efforts, open an
   issue.

   Please submit your custom themes if you would like them to be included in
   stig.

** License
   stig is free software: you can redistribute it and/or modify it under the
   terms of the GNU General Public License as published by the Free Software
   Foundation, either version 3 of the License, or (at your option) any later
   version.

   This program is distributed in the hope that it will be useful but WITHOUT
   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
   FOR A PARTICULAR PURPOSE.  See the [[https://www.gnu.org/licenses/gpl-3.0.txt][GNU General Public License]] for more
   details.

#+STARTUP: showeverything
#+OPTIONS: num:nil
#+OPTIONS: ^:{}
