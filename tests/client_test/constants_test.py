from stig.client.constants import (get_constant, is_constant)

def test_simple():
    c = get_constant('foo')
    assert str(c) == 'foo'
    assert repr(c) == '<Constant: FOO>'

def test_base_class():
    c = get_constant('Bar', bases=(int,), init_value=24)
    assert c == 24
    assert str(c) == 'Bar'
    assert repr(c) == '<Constant: BAR>'

def test_persistence():
    c = get_constant('baz', bases=(float,), init_value=6.5)
    assert c is get_constant('baz')
