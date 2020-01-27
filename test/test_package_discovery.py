# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_discovery import _discover_packages
from colcon_core.package_discovery import _get_extensions_with_parameters
from colcon_core.package_discovery import add_package_discovery_arguments
from colcon_core.package_discovery import discover_packages
from colcon_core.package_discovery import get_package_discovery_extensions
from colcon_core.package_discovery import PackageDiscoveryExtensionPoint
from mock import Mock
from mock import patch

from .entry_point_context import EntryPointContext


class Extension1(PackageDiscoveryExtensionPoint):
    PRIORITY = 80


class Extension2(PackageDiscoveryExtensionPoint):
    pass


class Extension3(PackageDiscoveryExtensionPoint):
    PRIORITY = 90


class Extension4(PackageDiscoveryExtensionPoint):
    pass


def test_get_package_discovery_extensions():
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        extensions = get_package_discovery_extensions()
        assert ['extension2', 'extension4', 'extension3', 'extension1'] == \
            list(extensions.keys())


def test_add_package_discovery_arguments():
    parser = Mock()
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        add_package_discovery_arguments(parser)

        all_extensions = get_package_discovery_extensions()

        extensions = {'extension2': all_extensions['extension2']}
        # mock the has_default method
        extensions['extension2'].has_default = Mock(
            side_effect=ValueError('exception in has_default'))
        with patch('colcon_core.package_discovery.logger.error') as error:
            add_package_discovery_arguments(parser, extensions=extensions)
            # the raised exception is catched and results in an error message
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in package discovery extension 'extension2': "
                'exception in has_default\n')

        extensions = {'extension3': all_extensions['extension3']}
        # mock the add_arguments method
        extensions['extension3'].add_arguments = Mock(
            side_effect=ValueError('exception in add_arguments'))
        with patch('colcon_core.package_discovery.logger.error') as error:
            add_package_discovery_arguments(parser, extensions=extensions)
            # the raised exception is catched and results in an error message
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in package discovery extension 'extension3': "
                'exception in add_arguments\n')

        # mock the has_default method and return True
        extensions['extension3'].has_default = Mock(return_value=True)
        add_package_discovery_arguments(parser, extensions=extensions)


def test_discover_packages():
    # check without any extensions
    with patch(
        'colcon_core.package_discovery.get_package_discovery_extensions',
        return_value={},
    ) as get_extensions:
        with patch('colcon_core.package_discovery.logger.warning') as warn:
            descs = discover_packages(None, None)
    assert get_extensions.call_count == 1
    warn.assert_called_once_with('No package discovery extensions found')
    assert descs == set()

    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        extensions = get_package_discovery_extensions()
        assert len(extensions) == 4

        # check without any parameters
        extensions['extension1'].discover = Mock(
            return_value={PackageDescriptor('/extension1/pkg1')})
        extensions['extension2'].discover = Mock(
            return_value={PackageDescriptor('/extension2/pkg1')})

        descs = discover_packages(None, None, discovery_extensions=extensions)
        assert len(descs) == 2
        expected_path = '/extension1/pkg1'.replace('/', os.sep)
        assert expected_path in (str(d.path) for d in descs)
        expected_path = '/extension2/pkg1'.replace('/', os.sep)
        assert expected_path in (str(d.path) for d in descs)

        # check with parameters
        extensions['extension3'].has_parameters = Mock(return_value=True)
        extensions['extension3'].discover = Mock(
            return_value={
                PackageDescriptor('/extension3/pkg1'),
                PackageDescriptor('/extension3/pkg2')})

        descs = discover_packages(None, None, discovery_extensions=extensions)
        assert len(descs) == 2
        expected_path = '/extension3/pkg1'.replace('/', os.sep)
        assert expected_path in (str(d.path) for d in descs)
        expected_path = '/extension3/pkg2'.replace('/', os.sep)
        assert expected_path in (str(d.path) for d in descs)


def test__get_extensions_with_parameters():
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        extensions = get_package_discovery_extensions()

        # mock the has_parameters method
        extensions['extension1'].has_parameters = Mock(return_value=True)
        extensions['extension2'].has_parameters = Mock(
            side_effect=ValueError('exception in has_parameters'))
        extensions['extension3'].has_parameters = Mock(
            side_effect=PackageDiscoveryExtensionPoint.has_parameters)
        extensions['extension4'].has_parameters = Mock(return_value=False)

        with_parameters = _get_extensions_with_parameters(Mock(), extensions)
        assert extensions['extension1'].has_parameters.call_count == 1
        assert extensions['extension2'].has_parameters.call_count == 1
        assert extensions['extension3'].has_parameters.call_count == 1
        assert extensions['extension4'].has_parameters.call_count == 1
        assert set(with_parameters.keys()) == {'extension1'}


def test__discover_packages():
    descs = _discover_packages(None, None, {})
    assert descs == set()

    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        extensions = get_package_discovery_extensions()

        # mock the discover method in the order the extensions are being called
        extensions['extension2'].discover = Mock(
            side_effect=ValueError('exception in discover'))
        extensions['extension4'].discover = Mock(
            side_effect=extensions['extension4'].discover)
        extensions['extension3'].discover = Mock(
            return_value={
                PackageDescriptor('/extension3/pkg1'),
                PackageDescriptor('/extension3/pkg2')})
        # returns None instead of a set
        extensions['extension1'].discover = Mock()

        with patch('colcon_core.package_discovery.logger.error') as error:
            descs = _discover_packages(Mock(), None, extensions)

            # in the order the extensions are being called
            assert extensions['extension2'].discover.call_count == 1
            assert extensions['extension4'].discover.call_count == 1
            assert extensions['extension3'].discover.call_count == 1
            assert extensions['extension1'].discover.call_count == 1

            # the raised exceptions are catched and result in error messages
            assert error.call_count == 2
            assert len(error.call_args_list[0][0]) == 1
            assert error.call_args_list[0][0][0].startswith(
                "Exception in package discovery extension 'extension2': "
                'exception in discover\n')
            assert len(error.call_args_list[1][0]) == 1
            assert error.call_args_list[1][0][0].startswith(
                "Exception in package discovery extension 'extension1': "
                'discover() should return a set\n')

        assert len(descs) == 2
        expected_path = '/extension3/pkg1'.replace('/', os.sep)
        assert expected_path in (str(d.path) for d in descs)
        expected_path = '/extension3/pkg2'.replace('/', os.sep)
        assert expected_path in (str(d.path) for d in descs)
