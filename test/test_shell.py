# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell import create_environment_hook
from colcon_core.shell import get_colcon_prefix_path
from colcon_core.shell import get_command_environment
from colcon_core.shell import get_environment_variables
from colcon_core.shell import get_shell_extensions
from colcon_core.shell import ShellExtensionPoint
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext
from .environment_context import EnvironmentContext
from .run_until_complete import run_until_complete


class Extension1(ShellExtensionPoint):
    PRIORITY = 90


class Extension2(ShellExtensionPoint):
    pass


def test_extension_interface():
    extension = Extension1()
    with pytest.raises(NotImplementedError):
        extension.create_prefix_script(None, None, None)
    with pytest.raises(NotImplementedError):
        extension.create_package_script(None, None, None)
    with pytest.raises(NotImplementedError):
        extension.create_hook_set_value(None, None, None, None, None)
    with pytest.raises(NotImplementedError):
        extension.create_hook_append_value(None, None, None, None, None)
    with pytest.raises(NotImplementedError):
        extension.create_hook_prepend_value(None, None, None, None, None)
    with pytest.raises(NotImplementedError):
        extension.create_hook_include_file(None, None, None, None)

    coroutine = extension.generate_command_environment(None, None, None)
    with pytest.raises(NotImplementedError):
        run_until_complete(coroutine)


def test_get_shell_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_shell_extensions()
    assert list(extensions.keys()) == [100, 90]
    assert list(extensions[100].keys()) == ['extension2']
    assert list(extensions[90].keys()) == ['extension1']


async def generate_command_environment(task_name, build_base, dependencies):
    return {'key': 'value'}


def test_get_command_environment():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_shell_extensions()

        # one not implemented, one skipped extension
        extensions[90]['extension1'].generate_command_environment = Mock(
            side_effect=SkipExtensionException())
        coroutine = get_command_environment(None, '/build/base', None)
        with patch('colcon_core.shell.logger.debug') as debug:
            with patch('colcon_core.shell.logger.info') as info:
                with pytest.raises(RuntimeError) as e:
                    run_until_complete(coroutine)
        assert 'Could not find a shell extension for the command environment' \
            in str(e)
        assert extensions[90]['extension1'].generate_command_environment \
            .call_count == 1
        # the raised exceptions are catched and result in a debug/info message
        assert debug.call_count == 1
        assert len(debug.call_args[0]) == 1
        assert debug.call_args[0][0] == \
            "Skip shell extension 'extension2' for command environment"
        assert info.call_count == 1
        assert len(info.call_args[0]) == 1
        assert info.call_args[0][0].startswith(
            "Skip shell extension 'extension1' for command environment: ")

        # raise runtime error
        extensions[100]['extension2'].generate_command_environment = Mock(
            side_effect=RuntimeError('custom exception'))
        extensions[90]['extension1'].generate_command_environment.reset_mock()
        coroutine = get_command_environment(None, '/build/base', None)
        with pytest.raises(RuntimeError) as e:
            run_until_complete(coroutine)
        assert str(e).endswith(': custom exception')
        assert extensions[90]['extension1'].generate_command_environment \
            .call_count == 0

        # one exception, one successful
        extensions[100]['extension2'].generate_command_environment = Mock(
            side_effect=Exception('custom exception'))
        extensions[90]['extension1'].generate_command_environment = Mock(
            side_effect=generate_command_environment)
        coroutine = get_command_environment(None, '/build/base', None)
        with patch('colcon_core.shell.logger.error') as error:
            env = run_until_complete(coroutine)
        assert env == {'key': 'value'}
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in shell extension 'extension2': custom exception\n")


def test_get_environment_variables():
    cmd = [
        'echo', 'NAME=value', '&&',
        'echo', '&&',
        'echo', 'SOMETHING', '&&',
        'echo', 'NAME2=value with spaces']

    coroutine = get_environment_variables(cmd)
    env = run_until_complete(coroutine)

    assert len(env.keys()) == 2
    assert 'NAME' in env.keys()
    assert env['NAME'] == 'value'
    assert 'NAME2' in env.keys()
    assert env['NAME2'] == 'value with spaces'


class Extension3(ShellExtensionPoint):
    PRIORITY = 105


class Extension4(ShellExtensionPoint):
    PRIORITY = 101


class Extension5(ShellExtensionPoint):
    PRIORITY = 110


def test_create_environment_hook():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        # no primary shell extension
        with pytest.raises(RuntimeError) as e:
            create_environment_hook(None, None, None, None, None)
        assert str(e).endswith(
            'Could not find a primary shell extension for creating an '
            'environment hook')

    with EntryPointContext(
        extension3=Extension3, extension4=Extension4, extension5=Extension5
    ):
        extensions = get_shell_extensions()

        # one invalid, two valid return values
        extensions[105]['extension3'].create_hook_prepend_value = Mock()
        extensions[101]['extension4'].create_hook_prepend_value = Mock(
            return_value=Path('/some/path/sub/hookA'))
        extensions[110]['extension5'].create_hook_prepend_value = Mock(
            return_value=Path('/some/path/sub/hookB'))
        with patch('colcon_core.shell.logger.error') as error:
            hooks = create_environment_hook(None, None, None, None, None)
        assert len(hooks) == 2
        assert str(hooks[0]) == '/some/path/sub/hookB'.replace('/', os.sep)
        assert str(hooks[1]) == '/some/path/sub/hookA'.replace('/', os.sep)
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in shell extension 'extension3': "
            'create_hook_prepend_value() should return a Path object')

        # invalid mode
        with pytest.raises(NotImplementedError):
            create_environment_hook(
                None, None, None, None, None, mode='invalid')


def test_get_colcon_prefix_path():
    # empty environment variable
    with EnvironmentContext(COLCON_PREFIX_PATH=''):
        prefix_path = get_colcon_prefix_path(skip='/path/to/skip')
        assert prefix_path == []

    # extra path separator
    with EnvironmentContext(COLCON_PREFIX_PATH=os.pathsep):
        prefix_path = get_colcon_prefix_path(skip='/path/to/skip')
        assert prefix_path == []

    with TemporaryDirectory(prefix='test_colcon_') as basepath:
        basepath = Path(basepath)
        with EnvironmentContext(COLCON_PREFIX_PATH=os.pathsep.join(
            [str(basepath), str(basepath)]
        )):
            # multiple results
            prefix_path = get_colcon_prefix_path(skip='/path/to/skip')
            assert prefix_path == [str(basepath), str(basepath)]

            # skipping results
            prefix_path = get_colcon_prefix_path(skip=str(basepath))
            assert prefix_path == []

        # skipping non-existing results
        with EnvironmentContext(COLCON_PREFIX_PATH=os.pathsep.join(
            [str(basepath), str(basepath / 'non-existing-sub')]
        )):
            prefix_path = get_colcon_prefix_path(skip='/path/to/skip')
            assert prefix_path == [str(basepath)]
            # cached result
            prefix_path = get_colcon_prefix_path(skip='/path/to/skip')
            assert prefix_path == [str(basepath)]
