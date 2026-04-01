# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path

from colcon_core.generic_decorator import GenericDecorator
from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.python_project.hook_caller import AsyncHookCaller
from colcon_core.python_project.hook_caller import get_hook_caller
from colcon_core.python_project.hook_caller_decorator import \
    decorate_hook_caller
from colcon_core.python_project.hook_caller_decorator import \
    HookCallerDecoratorExtensionPoint

from .extension_point_context import ExtensionPointContext
from .run_until_complete import run_until_complete


TEST_ARTIFACTS_PATH = Path(__file__).parent / 'test_hook_caller'


def test_async_hook_caller_list_hooks():
    env = {
        **os.environ,
        'PYTHONPATH': os.pathsep.join((
            str(TEST_ARTIFACTS_PATH / 'mock_backends'),
            os.environ.get('PYTHONPATH', ''),
        )),
    }

    caller = AsyncHookCaller('mock_backend', env=env)

    hooks = run_until_complete(caller.list_hooks())
    assert sorted(hooks) == [
        'build_sdist',
        'build_wheel',
        'custom_hook',
    ]


def test_async_hook_caller_list_hooks_object():
    env = {
        **os.environ,
        'PYTHONPATH': os.pathsep.join((
            str(TEST_ARTIFACTS_PATH / 'mock_backends'),
            os.environ.get('PYTHONPATH', ''),
        )),
    }

    caller = AsyncHookCaller('mock_backend_obj:backend_instance', env=env)

    hooks = run_until_complete(caller.list_hooks())
    assert sorted(hooks) == [
        'build_sdist',
        'build_wheel',
        'custom_hook',
    ]


def test_async_hook_caller_call_hook():
    env = {
        **os.environ,
        'PYTHONPATH': os.pathsep.join((
            str(TEST_ARTIFACTS_PATH / 'mock_backends'),
            os.environ.get('PYTHONPATH', ''),
        )),
    }

    stdout_log = []
    stderr_log = []

    def stdout_callback(data):
        stdout_log.append(data)

    def stderr_callback(data):
        stderr_log.append(data)

    caller = AsyncHookCaller(
        'mock_backend', env=env,
        stdout_callback=stdout_callback, stderr_callback=stderr_callback)

    res = run_until_complete(caller.call_hook('custom_hook', a=3, b=4))
    assert res == 7

    res = run_until_complete(caller.call_hook('custom_hook', a=3))
    assert res == 5


def test_async_hook_caller_call_hook_object():
    env = {
        **os.environ,
        'PYTHONPATH': os.pathsep.join((
            str(TEST_ARTIFACTS_PATH / 'mock_backends'),
            os.environ.get('PYTHONPATH', ''),
        )),
    }

    caller = AsyncHookCaller('mock_backend_obj:backend_instance', env=env)

    res = run_until_complete(caller.call_hook('custom_hook', a=5, b=5))
    assert res == 10


def test_get_hook_caller_default_spec():
    # An empty directory has no pyproject.toml, so it uses default spec
    empty_dir = TEST_ARTIFACTS_PATH / 'empty'
    desc = PackageDescriptor(str(empty_dir))

    caller = get_hook_caller(desc)

    assert caller.backend_name == 'setuptools.build_meta:__legacy__'


def test_get_hook_caller_with_backend_path():
    proj_dir = TEST_ARTIFACTS_PATH / 'with_backend_path'
    desc = PackageDescriptor(str(proj_dir))

    env = {'PYTHONPATH': 'initial_path'}
    caller = get_hook_caller(desc, env=env)

    assert caller.backend_name == 'mock_backend'

    # The backend path items are added to the beginning of PYTHONPATH
    assert caller.env['PYTHONPATH'] == os.pathsep.join((
        'mock_backend_dir',
        'another_dir',
        'initial_path',
    ))


def test_get_hook_caller_with_backend_path_no_pythonpath():
    proj_dir = TEST_ARTIFACTS_PATH / 'with_backend_path_no_pythonpath'
    desc = PackageDescriptor(str(proj_dir))

    caller = get_hook_caller(desc, env={})

    assert caller.backend_name == 'mock_backend'

    # 'mock_backend_dir' is the only element, no trailing path separator
    assert caller.env['PYTHONPATH'] == 'mock_backend_dir'


class MockDecoratorExtension(HookCallerDecoratorExtensionPoint):
    """
    Testing extension point for hook caller decoration.

    This extension demonstrates how to apply a decorator to a specific backend.
    """

    class DecoratedHookCaller(GenericDecorator):
        """
        Testing class for hook caller decoration.

        This decorator modifies the default value of the ``b`` argument of the
        ``custom_hook`` function.
        """

        async def call_hook(self, hook_name, **kwargs):
            if hook_name == 'custom_hook' and 'b' not in kwargs:
                kwargs['b'] = 10
            return await self._decoree.call_hook(hook_name, **kwargs)

    def decorate_hook_caller(self, *, hook_caller):
        if hook_caller.backend_name != 'mock_backend_obj:backend_instance':
            return hook_caller

        return self.DecoratedHookCaller(hook_caller)


def test_decorate_hook_caller():
    env = {
        **os.environ,
        'PYTHONPATH': os.pathsep.join((
            str(TEST_ARTIFACTS_PATH / 'mock_backends'),
            os.environ.get('PYTHONPATH', ''),
        )),
    }

    caller_obj = AsyncHookCaller('mock_backend_obj:backend_instance', env=env)
    caller_mod = AsyncHookCaller('mock_backend', env=env)

    with ExtensionPointContext(mock_decorator=MockDecoratorExtension):
        decorated_obj = decorate_hook_caller(caller_obj)
        decorated_mod = decorate_hook_caller(caller_mod)

    # Object backend custom_hook: b=5 -> 10, b=default(10) -> 15
    res = run_until_complete(decorated_obj.call_hook('custom_hook', a=5, b=5))
    assert res == 10

    res = run_until_complete(decorated_obj.call_hook('custom_hook', a=5))
    assert res == 15

    # Module backend custom_hook: unaffected, b=5 -> 10, b=default(2) -> 7
    res = run_until_complete(decorated_mod.call_hook('custom_hook', a=5, b=5))
    assert res == 10

    res = run_until_complete(decorated_mod.call_hook('custom_hook', a=5))
    assert res == 7
