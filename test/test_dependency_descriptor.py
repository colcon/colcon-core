# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.dependency_descriptor import DependencyDescriptor


def test_constructor():
    d = DependencyDescriptor('foo')
    assert d == 'foo'
    assert str(d) == 'foo'
    assert d.name == 'foo'
    assert len(d.metadata) == 0

    d = DependencyDescriptor('foo', metadata={'bar': 'baz'})
    assert d == 'foo'
    assert str(d) == 'foo'
    assert d.name == 'foo'
    assert len(d.metadata) == 1
    assert 'bar' in d.metadata
    assert d.metadata['bar'] == 'baz'
