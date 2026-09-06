# Copyright 2026 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import sys

from colcon_core.environment_variable import EnvironDict
from colcon_core.environment_variable import EnvironmentVariable
import pytest


def test_environment_variable():
    ev = EnvironmentVariable('NAME', 'desc')
    assert ev.name == 'NAME'
    assert ev.description == 'desc'


def test_environ_dict():
    if sys.platform == 'win32':
        return _test_environ_dict_win32()
    else:
        return _test_environ_dict_posix()


def _test_environ_dict_win32():
    # Test initialization
    env = EnvironDict({'Foo': 'bar'})
    assert len(env) == 1

    # Test case-insensitive get
    assert env['foo'] == 'bar'
    assert env['FOO'] == 'bar'
    assert env['Foo'] == 'bar'

    # Test case-insensitive set and casing preservation
    env['foo'] = 'baz'
    assert env['Foo'] == 'baz'
    assert list(env) == ['Foo']

    # Test kwargs init
    env2 = EnvironDict(Foo='bar')
    assert env2['foo'] == 'bar'

    # Test __iter__ yields properly cased keys
    env3 = EnvironDict()
    env3['MiXed'] = 'val'
    assert list(env3) == ['MiXed']

    # Test upper_items
    assert list(env3.upper_items()) == [('MIXED', 'val')]

    # Test __eq__
    assert env3 == {'mixed': 'val'}
    assert env3 == EnvironDict({'MIXED': 'val'})
    assert env3 != {'mixed': 'other'}
    assert env3 != 42

    # Test copy
    env3_copy = env3.copy()
    assert env3_copy == env3
    assert list(env3_copy) == ['MiXed']

    # Test delete
    del env3['mIxEd']
    assert len(env3) == 0
    with pytest.raises(KeyError):
        _ = env3['MiXed']

    # Test __repr__
    env4 = EnvironDict({'A': '1'})
    assert repr(env4) == "{'A': '1'}"


def _test_environ_dict_posix():
    env = EnvironDict()
    env['Foo'] = 'bar'
    assert env['Foo'] == 'bar'

    # On POSIX it should be case-sensitive
    with pytest.raises(KeyError):
        _ = env['foo']
