# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from argparse import Namespace
import os

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_selection import _add_package_selection_arguments
from colcon_core.package_selection import _check_package_selection_parameters
from colcon_core.package_selection import add_arguments
from colcon_core.package_selection import get_package_selection_extensions
from colcon_core.package_selection import get_packages
from colcon_core.package_selection import PackageSelectionExtensionPoint
from colcon_core.package_selection import select_package_decorators
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


class Extension1(PackageSelectionExtensionPoint):
    pass


class Extension2(PackageSelectionExtensionPoint):
    pass


def test_get_package_selection_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_selection_extensions()
        assert ['extension1', 'extension2'] == list(extensions.keys())


def add_dummy_arguments(parser):
    parser.add_argument('arg')


def test__add_package_selection_arguments():
    parser = Mock()
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_selection_extensions()

        # invalid return value
        extensions['extension1'].add_arguments = Mock(return_value=True)
        with patch(
            'colcon_core.package_selection.add_package_discovery_arguments'
        ) as add_package_discovery_arguments:
            with patch('colcon_core.package_selection.logger.error') as error:
                add_arguments(parser)
        assert add_package_discovery_arguments.call_count == 1
        # the raised assertion is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in package selection extension 'extension1': "
            'add_arguments() should return None\n')

        # raise exception
        extensions['extension1'].add_arguments = Mock(
            side_effect=RuntimeError('custom exception'))
        # check that arguments can be added
        extensions['extension2'].add_arguments = Mock(
            side_effect=add_dummy_arguments)
        with patch('colcon_core.package_selection.logger.error') as error:
            _add_package_selection_arguments(parser)
        assert extensions['extension2'].add_arguments.call_count == 1
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in package selection extension 'extension1': "
            'custom exception\n')


def test_get_packages():
    args = Namespace()
    d1 = PackageDescriptor('/some/path')
    d1.name = 'one'
    d2 = PackageDescriptor('/other/path')
    d2.name = 'two'
    with patch(
        'colcon_core.package_selection.discover_packages',
        return_value=[d1, d2]
    ):
        decos = get_packages(args)
    assert len(decos) == 2
    assert decos[0].descriptor.name == 'one'
    assert decos[0].selected is True
    assert decos[1].descriptor.name == 'two'
    assert decos[1].selected is True

    d2.name = 'one'
    with patch(
        'colcon_core.package_selection.discover_packages',
        return_value=[d1, d2]
    ):
        with pytest.raises(RuntimeError) as e:
            get_packages(args)
        assert 'Duplicate package names not supported:' in str(e.value)
        assert '- one:' in str(e.value)
        assert '- {sep}some{sep}path'.format(sep=os.sep) in str(e.value)
        assert '- {sep}other{sep}path'.format(sep=os.sep) in str(e.value)


def test__check_package_selection_parameters():
    args = Mock()
    pkg_names = Mock()

    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_selection_extensions()

        # nothing wrong with the arguments
        _check_package_selection_parameters(args, pkg_names)

        # raise exception
        extensions['extension1'].check_parameters = Mock(
            side_effect=RuntimeError('custom exception'))
        extensions['extension2'].check_parameters = Mock(return_value=None)
        with patch('colcon_core.package_selection.logger.error') as error:
            _check_package_selection_parameters(args, pkg_names)
        assert extensions['extension2'].check_parameters.call_count == 1
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in package selection extension 'extension1': custom "
            'exception\n')

        # invalid return value
        extensions['extension1'].check_parameters = Mock(return_value=True)
        extensions['extension2'].check_parameters.reset_mock()
        with patch('colcon_core.package_selection.logger.error') as error:
            _check_package_selection_parameters(args, pkg_names)
        assert extensions['extension2'].check_parameters.call_count == 1
        # the raised assertion is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in package selection extension 'extension1': "
            'check_parameters() should return None\n')

        # select some packages
        extensions['extension1'].check_parameters = Mock(
            side_effect=SystemExit(1))
        with pytest.raises(SystemExit):
            _check_package_selection_parameters(args, pkg_names)


def select_some_packages(*, args, decorators):
    for i, decorator in enumerate(decorators):
        decorator.selected = bool(i % 2)


def test_select_package_decorators():
    args = Mock()
    deco1 = Mock()
    deco1.selected = True
    deco2 = Mock()
    deco2.selected = True
    decos = [deco1, deco2]

    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_selection_extensions()

        # raise exception
        extensions['extension2'].select_packages = Mock(return_value=None)
        with patch('colcon_core.package_selection.logger.error') as error:
            select_package_decorators(args, decos)
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in package selection extension 'extension1': \n")

        # invalid return value
        extensions['extension1'].select_packages = Mock(return_value=True)
        with patch('colcon_core.package_selection.logger.error') as error:
            select_package_decorators(args, decos)
        # the raised assertion is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in package selection extension 'extension1': "
            'select_packages() should return None\n')

        # select some packages
        extensions['extension1'].select_packages = Mock(
            side_effect=select_some_packages)
        select_package_decorators(args, decos)
        assert not deco1.selected
        assert deco2.selected
