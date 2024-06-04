# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from unittest.mock import Mock
from unittest.mock import patch

from colcon_core.command import CommandContext
from colcon_core.package_decorator import get_decorators
from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.plugin_system import satisfies_version
from colcon_core.task import TaskExtensionPoint
from colcon_core.verb.test import TestVerb
import pytest


class NoopTestTask(TaskExtensionPoint):

    TASK_NAME = 'test'
    PACKAGE_TYPE = 'baz'

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(TaskExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    async def test(self, *, additional_hooks=None):
        pass


@pytest.fixture(scope='module', autouse=True)
def patch_other_extension_args():
    with patch('colcon_core.verb.test.add_event_handler_arguments'), \
            patch('colcon_core.verb.test.add_executor_arguments'), \
            patch('colcon_core.verb.test.add_packages_arguments'), \
            patch('colcon_core.verb.test.add_task_arguments'):
        yield


@pytest.fixture(scope='module', autouse=True)
def patch_get_task_extension():
    with patch(
        'colcon_core.verb.test.get_task_extension',
        return_value=NoopTestTask(),
    ) as get_task_extension:
        yield get_task_extension


@pytest.fixture(scope='module', autouse=True)
def patch_get_packages():
    desc1 = PackageDescriptor('foo_bar')
    desc1.type = 'foo'
    desc1.name = 'bar'

    desc2 = PackageDescriptor('foo_baz')
    desc2.type = 'foo'
    desc2.name = 'baz'

    descriptors = {desc1, desc2}
    decorators = get_decorators(descriptors)

    for decorator in decorators:
        decorator.recursive_dependencies = []

    for decorator in decorators:
        decorator.selected = False
        break

    with patch(
        'colcon_core.verb.test.get_packages',
        return_value=decorators,
    ) as get_packages:
        yield get_packages


@pytest.fixture(scope='module', autouse=True)
def patch_execute_jobs():
    with patch(
        'colcon_core.verb.test.execute_jobs',
        return_value=0,
    ) as execute_jobs:
        yield execute_jobs


def test_add_arguments():
    extension = TestVerb()
    parser = Mock()
    parser.add_argument = Mock()
    extension.add_arguments(parser=parser)
    # This extension calls argument adders from other extensions.
    # Verify only that *some* arguments were added.
    assert parser.add_argument.call_count > 4


def test_verb_test(tmpdir):
    extension = TestVerb()
    extension.add_arguments(parser=Mock())

    context = CommandContext(
        command_name='colcon',
        args=Mock())

    context.args.build_base = os.path.join(tmpdir, 'build')
    context.args.install_base = os.path.join(tmpdir, 'install')
    context.args.test_result_base = os.path.join(tmpdir, 'test_results')

    assert 0 == extension.main(context=context)
