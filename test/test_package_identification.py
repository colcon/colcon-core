# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_identification import _identify
from colcon_core.package_identification \
    import get_package_identification_extensions
from colcon_core.package_identification import identify
from colcon_core.package_identification import IgnoreLocationException
from colcon_core.package_identification \
    import PackageIdentificationExtensionPoint
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


class Extension1(PackageIdentificationExtensionPoint):
    PRIORITY = 80


class Extension2(PackageIdentificationExtensionPoint):
    pass


class Extension3(PackageIdentificationExtensionPoint):
    PRIORITY = 90


class Extension4(PackageIdentificationExtensionPoint):
    pass


def test_get_package_identification_extensions():
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        extensions = get_package_identification_extensions()
    assert list(extensions.keys()) == [100, 90, 80]
    assert list(extensions[100].keys()) == ['extension2', 'extension4']
    assert list(extensions[90].keys()) == ['extension3']
    assert list(extensions[80].keys()) == ['extension1']


def identify_name(desc):
    desc.name = 'name'


def identify_type(desc):
    desc.type = 'type'


def identify_name_and_type(desc):
    identify_name(desc)
    identify_type(desc)


def test_identify():
    path = '/some/path'
    context = EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4)

    with context:
        # no identification
        desc = identify({}, path)
        assert desc is None

        # no complete identification
        extensions = get_package_identification_extensions()
        extensions[80]['extension1'].identify = Mock(
            side_effect=identify_name)
        desc = identify(extensions, path)
        assert desc is None

        # valid result combined across priority groups
        extensions = get_package_identification_extensions()
        extensions[100]['extension4'].identify = Mock(
            side_effect=identify_type)
        desc = identify(extensions, path)
        assert isinstance(desc, PackageDescriptor)
        assert str(desc.path) == '/some/path'.replace('/', os.sep)
        assert desc.name == 'name'
        assert desc.type == 'type'

        # skip location
        extensions = get_package_identification_extensions()
        extensions[90]['extension3'].identify = Mock(
            side_effect=IgnoreLocationException())
        with pytest.raises(IgnoreLocationException):
            identify(extensions, path)

        # valid result from first priority group
        # lower priority groups are not even invoked
        extensions = get_package_identification_extensions()
        extensions[100]['extension4'].identify.side_effect = \
            identify_name_and_type
        desc = identify(extensions, path)
        assert isinstance(desc, PackageDescriptor)
        assert str(desc.path) == '/some/path'.replace('/', os.sep)
        assert desc.name == 'name'
        assert desc.type == 'type'

    with context:
        # multiple different results result in skipping the location
        extensions = get_package_identification_extensions()
        extensions[100]['extension2'].identify = Mock(
            side_effect=identify_name)
        extensions[100]['extension4'].identify = Mock(
            side_effect=identify_type)
        with pytest.raises(IgnoreLocationException):
            identify(extensions, path)


def test__identify():
    desc_path_only = PackageDescriptor('/some/path')
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2,
        extension3=Extension3, extension4=Extension4,
    ):
        # valid result
        extensions = get_package_identification_extensions()[100]
        extensions['extension2'].identify = Mock()
        extensions['extension4'].identify = identify_name_and_type
        desc = _identify(extensions, desc_path_only)
        assert isinstance(desc, PackageDescriptor)
        assert str(desc.path) == '/some/path'.replace('/', os.sep)
        assert desc.name == 'name'
        assert desc.type == 'type'

        # no results
        extensions = get_package_identification_extensions()[100]
        extensions['extension2'].identify = Mock()
        extensions['extension4'].identify = Mock()
        desc = _identify(extensions, desc_path_only)
        assert desc is None

        # multiple different results
        extensions = get_package_identification_extensions()[100]
        extensions['extension2'].identify = identify_name
        extensions['extension4'].identify = identify_type
        with patch(
            'colcon_core.package_identification.logger.warning'
        ) as warn:
            desc = _identify(extensions, desc_path_only)
            assert desc is False
            # the raised exception is catched and results in a warn message
            assert warn.call_count == 1
            assert len(warn.call_args[0]) == 1
            assert 'multiple matches' in warn.call_args[0][0]

        # invalid return value
        extensions = get_package_identification_extensions()[90]
        extensions['extension3'].identify = Mock(return_value=True)
        with patch('colcon_core.package_identification.logger.error') as error:
            desc = _identify(extensions, desc_path_only)
            assert desc is None
            # the raised exception is catched and results in an error message
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in package identification extension 'extension3' "
                "in '/some/path': identify() should return None\n"
                .replace('/', os.sep))

        # skip location
        extensions = get_package_identification_extensions()[90]
        extensions['extension3'].identify = Mock(
            side_effect=IgnoreLocationException())
        with pytest.raises(IgnoreLocationException):
            _identify(extensions, desc_path_only)

        # raise exception
        extensions = get_package_identification_extensions()[90]
        extensions['extension3'].identify = Mock(
            side_effect=RuntimeError('custom exception'))
        with patch('colcon_core.package_identification.logger.error') as error:
            desc = _identify(extensions, desc_path_only)
            assert desc is None
            # the raised exception is catched and results in an error message
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in package identification extension 'extension3' "
                "in '/some/path': custom exception\n".replace('/', os.sep))
