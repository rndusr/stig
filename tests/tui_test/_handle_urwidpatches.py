import sys


def setUpModule():
    # Monkey-patch stuff in the urwid module in-place
    from stig.tui import urwidpatches
    urwidpatches.apply_patches()

    import urwid
    assert hasattr(urwid.ListBox, 'get_scrollpos')
    assert ' ' not in urwid.command_map._command

def tearDownModule(self):
    # Remove monkey patches
    from stig.tui import urwidpatches
    urwidpatches.revert_patches()

    import urwid
    assert not hasattr(urwid.ListBox, 'get_scrollpos')
    assert ' ' in urwid.command_map._command
