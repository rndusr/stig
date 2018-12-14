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


def make_X_FILTER_spec(filtername, or_focused=False, more_text='', **kwargs):
    spec = { 'names': (filtername.upper() + ' FILTER',),
             'description': ('%s filter expression (see %s FILTERS section in `help filter`)' %
                             (filtername.capitalize(), filtername.upper()))}
    if or_focused:
        spec['description'] += ' or focused %s in the TUI if omitted' % filtername.lower()
    if more_text:
        spec['description'] += '; %s' % more_text
    spec.update(**kwargs)
    return spec


def make_SCRIPTING_doc(cmdname):
    return ( ("If invoked as a command line argument and the output does not "
              "go to a TTY (i.e. the terminal size can't be determined), "
              "the output is optimized for scripting.  Numbers are "
              "unformatted, columns are separated by a horizontal tab "
              "character ('\\t') and headers are not printed."),
             "",
             ("To enforce human-readable, formatted output, set the environment "
              "variables COLUMNS and LINES."),
             "",
             "\t$ \tCOLUMNS=80 LINES=24 {{__appname__}} {CMDNAME} | less -R".format(CMDNAME=cmdname) )


def make_SORT_ORDERS_doc(sortercls, option, setting, append=()):
    doc = [('The following sort orders can be specified with the {option} option '
            'or the "{setting}" setting:').format(option=option, setting=setting),
            '']

    for sname,s in sorted(sortercls.SORTSPECS.items()):
        snames = ', '.join((sname,) + s.aliases)
        doc.append('\t{}\t - \t{}'.format(snames, s.description))

    doc.extend(('',
                'Multiple sort orders are separated with "," without spaces.',
                '',
                'Sorting is reversed if the sort order is prepended by "!" or ".".',
                '',
                ('If "%s" is not given explicitly, it is always prepended to '
                 'the list of sort orders.') % sortercls.DEFAULT_SORT))
    if append:
        doc.extend(('',) + append)
    return tuple(doc)


def make_COLUMNS_doc(columnspecs, option, setting, append=()):
    return (('The following columns can be specified with the {option} option '
             'or the "{setting}" setting:').format(option=option, setting=setting),
            '',
            '\t%s' % ', '.join(sorted(columnspecs)),
            '',
            'Columns are separated with "," without spaces.') + append
