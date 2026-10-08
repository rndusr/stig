
def setUpModule():
    # Monkey-patch stuff in the urwid module in-place
    from stig.tui import urwidpatches
    urwidpatches.apply_patches()

    import urwid
    assert urwid.ListBox.__name__ == 'ListBox_patched', urwid.ListBox
    assert ' ' not in urwid.command_map._command

def tearDownModule(self):
    # Remove monkey patches
    from stig.tui import urwidpatches
    urwidpatches.revert_patches()

    import urwid
    assert urwid.ListBox.__name__ != 'ListBox_patched', urwid.ListBox
    assert ' ' in urwid.command_map._command
