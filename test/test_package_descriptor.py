# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
import os
from pathlib import Path
from unittest.mock import patch

from colcon_core.dependency_descriptor import DependencyDescriptor
from colcon_core.package_descriptor import PackageDescriptor
import pytest


def test_constructor():
    d = PackageDescriptor('/some/path')
    assert d.path == Path('/some/path')
    assert d.type is None
    assert d.name is None
    assert len(d.dependencies.keys()) == 0
    assert len(d.hooks) == 0
    assert len(d.metadata.keys()) == 0


def test_identifies_package():
    d = PackageDescriptor('/some/path')
    assert not d.identifies_package()
    d.type = 'type'
    assert not d.identifies_package()
    d.type = None
    d.name = 'name'
    assert not d.identifies_package()
    d.type = 'type'
    assert d.identifies_package()


def test_get_dependencies():
    d1 = PackageDescriptor('/some/path')
    d1.name = 'self'
    d1.dependencies['build'].add('build-depend')
    d1.dependencies['build'].add('depend')
    d1.dependencies['run'].add('run-depend')
    d1.dependencies['run'].add('depend')
    assert d1.get_dependencies() == {'build-depend', 'run-depend', 'depend'}

    d1.dependencies['test'].add('self')
    assert d1.get_dependencies(categories=('build', )) == \
        {'build-depend', 'depend'}

    with pytest.raises(AssertionError) as e:
        d1.get_dependencies()
    assert "'self'" in str(e.value)


@pytest.fixture
def recursive_dependencies():
    d = PackageDescriptor('/some/path')
    d.name = 'A'
    d.dependencies['build'].add('B')
    d.dependencies['run'].add('c')
    d.dependencies['test'].add('d')

    d1 = PackageDescriptor('/other/path')
    d1.name = 'B'
    d1.dependencies['build'].add(DependencyDescriptor('e'))
    d1.dependencies['run'].add(DependencyDescriptor('F'))
    d1.dependencies['test'].add(DependencyDescriptor('G'))

    d2 = PackageDescriptor('/another/path')
    d2.name = 'd'

    d3 = PackageDescriptor('/yet-another/path')
    d3.name = 'F'
    d3.dependencies['build'].add('h')
    d3.dependencies['test'].add('G')
    d3.dependencies['test'].add('I')
    d3.dependencies['test'].add('J')

    d4 = PackageDescriptor('/more/path')
    d4.name = 'G'
    d4.dependencies['test'].add('I')

    d5 = PackageDescriptor('/yet-more/path')
    d5.name = 'I'
    d5.dependencies['build'].add('K')
    # circular dependencies should be ignored
    d5.dependencies['run'].add('A')

    d6 = PackageDescriptor('/paths/galore')
    d6.name = 'J'

    d7 = PackageDescriptor('/never/enough/paths')
    d7.name = 'K'

    return d, {d, d1, d2, d3, d4, d5, d6, d7}


@patch(
    'colcon_core.feature_flags.get_feature_flags',
    lambda: ['restore_build_isolation'])
def test_get_recursive_dependencies(recursive_dependencies):
    desc, all_descs = recursive_dependencies
    rec_deps = desc.get_recursive_dependencies(
        all_descs,
        direct_categories=('build', 'run'),
        recursive_categories=('run', 'test'))
    assert rec_deps == {
        # direct dependencies
        'B',
        # recursive dependencies
        'F', 'G', 'I', 'J',
    }


@patch(
    'colcon_core.feature_flags.get_feature_flags',
    lambda: ['restore_build_isolation'])
def test_get_recursive_dependencies_map(recursive_dependencies):
    recursive_categories = defaultdict(lambda: ('run', 'test'))
    recursive_categories['run'] = ('run',)

    desc, all_descs = recursive_dependencies
    rec_deps = desc.get_recursive_dependencies(
        all_descs,
        direct_categories=('build', 'run'),
        recursive_categories=recursive_categories)
    assert rec_deps == {
        # direct dependencies
        'B',
        # recursive dependencies
        'F', 'G', 'I',
    }


def test_magic_methods():
    d1 = PackageDescriptor('/some/path')
    d1.type = 'custom-type'
    d1.name = 'custom-name'
    d2 = PackageDescriptor('/some/path')
    d2.type = 'custom-type'
    d2.name = 'other-name'
    assert d1 != d2
    assert hash(d1) != hash(d2)

    d2.name = 'custom-name'
    assert d1 == d2
    assert hash(d1) == hash(d2)

    d1.dependencies['build'].add('build-depend')
    d2.hooks.append('hook')
    d2.metadata['key'] = 'value'
    assert d1 == d2
    assert hash(d1) == hash(d2)

    d2.type = 'other-type'
    assert d1 != d2
    assert hash(d1) != hash(d2)

    d2.type = 'custom-type'
    assert d1 == d2
    assert hash(d1) == hash(d2)

    d2.path = Path('/other/path')
    assert d1 != d2

    # comparing with other types always returns False
    assert d1 != []


def test_str():
    d = PackageDescriptor('/some/path')
    d.type = 'custom-type'
    d.name = 'custom-name'
    d.dependencies['build'].add('build-depend')
    d.dependencies['run'].add('run-depend')
    d.hooks += ('hook-a', 'hook-b')
    d.metadata['key'] = 'value'
    s = str(d)
    assert s.startswith('{')
    assert s.endswith('}')
    assert 'path: ' in s
    assert '/some/path'.replace('/', os.sep) in s
    assert 'type: ' in s
    assert 'custom-type' in s
    assert 'name: ' in s
    assert 'custom-name' in s
    assert 'dependencies: ' in s
    assert 'build-depend' in s
    assert 'run-depend' in s
    assert 'hooks: ' in s
    assert 'hook-a' in s
    assert 'metadata: ' in s
    assert 'value' in s
