# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.topological_order import topological_order_packages
import pytest


def test_topological_order_packages():
    d1 = PackageDescriptor('/some/path')
    d1.name = 'a'
    d1.dependencies['build'].add('c')
    d2 = PackageDescriptor('/other/path')
    d2.name = 'b'
    d2.dependencies['run'].add('c')

    d3 = PackageDescriptor('/another/path')
    d3.name = 'c'
    d3.dependencies['build'].add('e')
    d3.dependencies['run'].add('f')
    d3.dependencies['test'].add('d')

    d4 = PackageDescriptor('/yet-another/path')
    d4.name = 'd'
    d4.dependencies['run'].add('f')
    d5 = PackageDescriptor('/more/path')
    d5.name = 'e'
    d5.dependencies['run'].add('f')

    d6 = PackageDescriptor('/yet-more/path')
    d6.name = 'f'

    decos = topological_order_packages(
        {d1, d2, d3, d4, d5, d6})
    names = [d .descriptor.name for d in decos]
    assert names == ['f', 'd', 'e', 'c', 'a', 'b']

    # ensure that input order doesn't affect the result
    decos = topological_order_packages(
        {d6, d5, d4, d3, d2, d1})
    names = [d .descriptor.name for d in decos]
    assert names == ['f', 'd', 'e', 'c', 'a', 'b']


def test_topological_order_packages_with_circular_dependency():
    d1 = PackageDescriptor('/some/path')
    d1.name = 'one'
    d1.dependencies['run'].add('two')

    d2 = PackageDescriptor('/other/path')
    d2.name = 'two'
    d2.dependencies['run'].add('three')

    d3 = PackageDescriptor('/another/path')
    d3.name = 'three'
    d3.dependencies['run'].add('one')
    d3.dependencies['run'].add('six')

    d4 = PackageDescriptor('/yet-another/path')
    d4.name = 'four'

    d5 = PackageDescriptor('/more/path')
    d5.name = 'five'
    d5.dependencies['run'].add('four')

    d6 = PackageDescriptor('/yet-more/path')
    d6.name = 'six'

    with pytest.raises(RuntimeError) as e:
        topological_order_packages({d1, d2, d3, d4})
    lines = str(e.value).splitlines()
    assert len(lines) == 4
    assert lines[0] == 'Unable to order packages topologically:'
    assert lines[1] == "one: ['three', 'two']"
    assert lines[2] == "three: ['one', 'two']"
    assert lines[3] == "two: ['one', 'three']"
