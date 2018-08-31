# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import copy

from colcon_core.dependency_descriptor import DependencyDescriptor


def test_constructor():
    name = 'ReallyCoolPackage'
    descriptor = DependencyDescriptor(name)
    assert descriptor.name == name
    assert len(descriptor.metadata.keys()) == 0


def test_metadata():
    metadata = {
        'foo': 'bar'
    }
    descriptor = DependencyDescriptor('CoolStuff',
                                      metadata=metadata)
    assert descriptor.metadata == metadata


def test_str():
    d = DependencyDescriptor('Package1')
    d.metadata['key'] = 'value'
    s = str(d)
    assert s.startswith('{')
    assert s.endswith('}')
    assert 'name: ' in s
    assert 'Package1' in s
    assert 'metadata: ' in s
    assert 'key' in s
    assert 'value' in s


def check_dependencies(actual, expected):
    """
    Check that all of the expected names are in actual

    :param actual: Set of DependencyDescriptor
    :param expected: List of str names
    :return: True if all expected names are in actual
    """
    if len(actual) != len(expected):
        return False

    deps = copy.copy(actual)

    for name in expected:
        descriptor = next(iter(
            [d for d in deps if d.name == name]), None)
        if descriptor is None:
            return False
        deps.remove(descriptor)
    assert len(deps) == 0
    return True
