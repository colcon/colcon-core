# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os

from colcon_core.package_augmentation import augment_packages
from colcon_core.package_augmentation \
    import get_package_augmentation_extensions
from colcon_core.package_augmentation import PackageAugmentationExtensionPoint
from colcon_core.package_augmentation import update_descriptor
from colcon_core.package_augmentation import update_metadata
from colcon_core.package_descriptor import PackageDescriptor
from mock import Mock
from mock import patch

from .entry_point_context import EntryPointContext


class Extension1(PackageAugmentationExtensionPoint):
    PRIORITY = 80


class Extension2(PackageAugmentationExtensionPoint):
    pass


def test_get_package_augmentation_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_augmentation_extensions()
        assert ['extension2', 'extension1'] == \
            list(extensions.keys())


def augment_package_metadata_with_data(desc, *, additional_argument_names):
    if str(desc.path) == '/some/path'.replace('/', os.sep):
        desc.metadata['key'] = 'value'


def augment_package_metadata_with_path(desc, *, additional_argument_names):
    desc.metadata['path'] = desc.path


def augment_package_with_hook(desc, *, additional_argument_names):
    desc.hooks += additional_argument_names


def test_augment_packages():
    desc1 = PackageDescriptor('/some/path')
    desc2 = PackageDescriptor('/other/path')
    descs = {desc1, desc2}
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_augmentation_extensions()
        extensions['extension1'].augment_package = Mock(
            side_effect=augment_package_metadata_with_data)
        extensions['extension2'].augment_package = Mock(
            side_effect=augment_package_metadata_with_path)
        augment_packages(descs)
    assert len(desc1.metadata) == 2
    assert set(desc1.metadata.keys()) == {'key', 'path'}
    assert desc1.path == desc1.metadata['path']

    assert len(desc2.metadata) == 1
    assert set(desc2.metadata.keys()) == {'path'}
    assert desc2.path == desc2.metadata['path']

    # raise exception
    desc1 = PackageDescriptor('/some/path')
    desc2 = PackageDescriptor('/other/path')
    descs = {desc1, desc2}
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_package_augmentation_extensions()
    extensions['extension1'].augment_package = Mock(
        side_effect=augment_package_with_hook)
    with patch('colcon_core.package_augmentation.logger.error') as error:
        augment_packages(
            descs, additional_argument_names=['arg1', 'arg2'],
            augmentation_extensions=extensions)
    assert desc1.hooks == ['arg1', 'arg2']
    assert desc2.hooks == ['arg1', 'arg2']
    # the raised exception is catched and results in an error message
    assert error.call_count == 1
    assert len(error.call_args[0]) == 1
    assert error.call_args[0][0].startswith(
        "Exception in package augmentation extension 'extension2': \n")

    # invalid return value
    desc1.hooks = []
    desc2.hooks = []
    extensions['extension2'].augment_packages = Mock(return_value=False)
    with patch('colcon_core.package_augmentation.logger.error') as error:
        augment_packages(
            descs, additional_argument_names=['arg1', 'arg2'],
            augmentation_extensions=extensions)
    assert desc1.hooks == ['arg1', 'arg2']
    assert desc2.hooks == ['arg1', 'arg2']
    # the raised assertion is catched and results in an error message
    assert error.call_count == 1
    assert len(error.call_args[0]) == 1
    assert error.call_args[0][0].startswith(
        "Exception in package augmentation extension 'extension2': ")


def test_update_descriptor():
    desc = PackageDescriptor('/some/path')
    assert len(desc.dependencies) == 0
    assert len(desc.hooks) == 0
    assert len(desc.metadata) == 0

    data = {
        'build-dependencies': {'b1', 'b2'},
        'test-dependencies': {'t1'},
    }
    update_descriptor(desc, data)
    assert len(desc.dependencies) == 2
    assert 'build' in desc.dependencies.keys()
    assert desc.dependencies['build'] == {'b1', 'b2'}
    assert 'test' in desc.dependencies.keys()
    assert desc.dependencies['test'] == {'t1'}

    data = {
        'dependencies': {'d1'},
        'hooks': ['hook1', 'hook2'],
        'key': 'value',
    }
    update_descriptor(desc, data, additional_argument_names=['*'])
    assert len(desc.dependencies) == 3
    assert 'build' in desc.dependencies.keys()
    assert desc.dependencies['build'] == {'d1', 'b1', 'b2'}
    assert 'run' in desc.dependencies.keys()
    assert desc.dependencies['run'] == {'d1'}
    assert 'test' in desc.dependencies.keys()
    assert desc.dependencies['test'] == {'d1', 't1'}

    assert len(desc.hooks) == 2
    assert desc.hooks == ['hook1', 'hook2']

    assert len(desc.metadata) == 1
    assert 'key' in desc.metadata
    assert desc.metadata['key'] == 'value'

    data = {
        'other': 'value',
        'some': 'value',
    }
    update_descriptor(
        desc, data, additional_argument_names=['some', 'unknown'])
    assert len(desc.metadata) == 2
    assert 'other' not in desc.metadata
    assert 'some' in desc.metadata
    assert desc.metadata['some'] == 'value'


def test_update_metadata():
    desc = PackageDescriptor('/some/path')
    desc.name = 'name'
    assert len(desc.metadata) == 0

    update_metadata(desc, 'd', {1: 'one', 2: 'two'})
    assert len(desc.metadata) == 1
    assert 'd' in desc.metadata.keys()
    assert desc.metadata['d'] == {1: 'one', 2: 'two'}

    update_metadata(desc, 'd', {2: 'TWO', 3: 'THREE'})
    assert len(desc.metadata) == 1
    assert 'd' in desc.metadata.keys()
    assert desc.metadata['d'] == {1: 'one', 2: 'TWO', 3: 'THREE'}

    update_metadata(desc, 'l', [1, 2])
    assert len(desc.metadata) == 2
    assert 'l' in desc.metadata.keys()
    assert desc.metadata['l'] == [1, 2]

    update_metadata(desc, 'l', [2, 3])
    assert len(desc.metadata) == 2
    assert 'l' in desc.metadata.keys()
    assert desc.metadata['l'] == [1, 2, 2, 3]

    update_metadata(desc, 's', {1, 2})
    assert len(desc.metadata) == 3
    assert 's' in desc.metadata.keys()
    assert desc.metadata['s'] == {1, 2}

    update_metadata(desc, 's', {2, 3})
    assert len(desc.metadata) == 3
    assert 's' in desc.metadata.keys()
    assert desc.metadata['s'] == {1, 2, 3}

    with patch('colcon_core.package_augmentation.logger.warning') as warn:
        update_metadata(desc, 's', 'different type')
    warn.assert_called_once_with(
        "update package 'name' metadata 's' from value '{1, 2, 3}' to "
        "'different type'")
    assert len(desc.metadata) == 3
    assert 's' in desc.metadata.keys()
    assert desc.metadata['s'] == 'different type'

    with patch('colcon_core.package_augmentation.logger.warning') as warn:
        update_metadata(desc, 's', 'same type')
    assert warn.call_count == 0
    assert len(desc.metadata) == 3
    assert 's' in desc.metadata.keys()
    assert desc.metadata['s'] == 'same type'
