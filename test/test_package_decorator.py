# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.package_decorator import add_recursive_dependencies
from colcon_core.package_decorator import get_decorators
from colcon_core.package_decorator import PackageDecorator
from colcon_core.package_descriptor import PackageDescriptor
from mock import Mock


def test_constructor():
    desc = Mock()
    d = PackageDecorator(desc)
    assert d.descriptor == desc
    assert d.recursive_dependencies is None
    assert d.selected is True


def test_get_decorators():
    desc1 = Mock()
    desc2 = Mock()
    decos = get_decorators([desc1, desc2])
    assert len(decos) == 2
    assert decos[0].descriptor == desc1
    assert decos[1].descriptor == desc2


def test_add_recursive_dependencies():
    d = PackageDescriptor('/some/path')
    d.name = 'A'
    d.dependencies['build'].add('B')
    d.dependencies['build'].add('c')
    d.dependencies['run'].add('D')
    d.dependencies['test'].add('e')

    d1 = PackageDescriptor('/other/path')
    d1.name = 'B'
    d1.dependencies['build'].add('f')
    d1.dependencies['run'].add('G')

    d2 = PackageDescriptor('/other/path')
    d2.name = 'D'
    d2.dependencies['run'].add('h')

    d3 = PackageDescriptor('/another/path')
    d3.name = 'G'
    d3.dependencies['build'].add('i')

    decos = get_decorators([d, d1, d2, d3])
    add_recursive_dependencies(
        decos, direct_categories={'build', 'run'},
        recursive_categories={'run'})

    assert decos[0].recursive_dependencies is not None
    assert decos[1].recursive_dependencies is not None
    assert decos[2].recursive_dependencies is not None
    assert decos[3].recursive_dependencies is not None
    assert decos[0].recursive_dependencies == {'B', 'D', 'G'}
