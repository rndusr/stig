import importlib
import sys


def setUpModule():
    # Monkey-patch stuff in the urwid module in-place
    if 'stig.tui.urwidpatches' not in sys.modules:
        import stig.tui.urwidpatches
    else:
        import stig.tui.urwidpatches
        importlib.reload(stig.tui.urwidpatches)
    import urwid
    assert hasattr(urwid.ListBox, 'get_scrollpos')
    assert ' ' not in urwid.command_map._command

def tearDownModule(self):
    # Remove monkey patches
    import urwid
    urwid.command_map.restore_defaults()
    importlib.reload(urwid)
    assert not hasattr(urwid.ListBox, 'get_scrollpos')
    assert ' ' in urwid.command_map._command
