import sys
import importlib

def setUpModule():
    # Monkey-patch stuff in the urwid module in-place
    if 'stig.tui.urwidpatches' not in sys.modules:
        import stig.tui.urwidpatches
    else:
        import stig.tui.urwidpatches
        importlib.reload(stig.tui.urwidpatches)
    import urwid
    assert hasattr(urwid.ListBox, 'get_scrollpos')

def tearDownModule(self):
    # Remove monkey patches
    import urwid
    importlib.reload(urwid)
    assert not hasattr(urwid.ListBox, 'get_scrollpos')
