# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import OrderedDict
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell import check_dependency_availability
from colcon_core.shell import create_environment_hook
from colcon_core.shell import find_installed_packages
from colcon_core.shell import find_installed_packages_in_environment
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
        extension.create_prefix_script(None, None)
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
            in str(e.value)
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
        assert str(e.value) == 'custom exception'
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
        'echo', 'FOO\nNAME=value\n\nSOMETHING\nNAME2=value with spaces']

    coroutine = get_environment_variables(cmd, shell=False)
    env = run_until_complete(coroutine)

    assert len(env.keys()) == 2
    assert 'NAME' in env.keys()
    assert env['NAME'] == 'value\nSOMETHING'
    assert 'NAME2' in env.keys()
    assert env['NAME2'] == 'value with spaces'

    # test with environment strings which isn't decodable
    async def check_output(cmd, **kwargs):
        return b'DECODE_ERROR=\x81\nNAME=value'
    with patch('colcon_core.shell.check_output', side_effect=check_output):
        with patch('colcon_core.shell.logger.warning') as warn:
            coroutine = get_environment_variables(['not-used'], shell=False)
            env = run_until_complete(coroutine)

    assert len(env.keys()) == 1
    assert 'NAME' in env.keys()
    assert env['NAME'] == 'value'
    # the raised decode error is catched and results in a warning message
    assert warn.call_count == 1
    assert len(warn.call_args[0]) == 1
    assert warn.call_args[0][0].startswith(
        "Failed to decode line from the environment using the encoding '")
    assert 'DECODE_ERROR=' in warn.call_args[0][0]


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
        assert str(e.value).endswith(
            'Could not find a primary shell extension for creating an '
            'environment hook')

    with EntryPointContext(
        extension3=Extension3, extension4=Extension4, extension5=Extension5
    ):
        extensions = get_shell_extensions()

        # append: one invalid, two valid return values
        extensions[105]['extension3'].create_hook_append_value = Mock()
        extensions[101]['extension4'].create_hook_append_value = Mock(
            return_value=Path('/some/path/sub/hookA'))
        extensions[110]['extension5'].create_hook_append_value = Mock(
            return_value=Path('/some/path/sub/hookB'))
        with patch('colcon_core.shell.logger.error') as error:
            hooks = create_environment_hook(
                None, None, None, None, None, mode='append')
        assert len(hooks) == 2
        assert str(hooks[0]) == '/some/path/sub/hookB'.replace('/', os.sep)
        assert str(hooks[1]) == '/some/path/sub/hookA'.replace('/', os.sep)
        # the raised exception is caught and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in shell extension 'extension3': "
            'create_hook_append_value() should return a Path object')

        # prepend: one invalid, two valid return values
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
        # the raised exception is caught and results in an error message
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
    # ignore deprecation warning
    with patch('colcon_core.shell.warnings.warn') as warn:
        # empty environment variable
        with EnvironmentContext(COLCON_PREFIX_PATH=''):
            prefix_path = get_colcon_prefix_path()
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
                with patch('colcon_core.shell.logger.warning') as warn:
                    prefix_path = get_colcon_prefix_path()
                assert prefix_path == [str(basepath)]
                assert warn.call_count == 1
                assert len(warn.call_args[0]) == 1
                assert warn.call_args[0][0].endswith(
                    "non-existing-sub' in the environment variable "
                    "COLCON_PREFIX_PATH doesn't exist")
                # suppress duplicate warning
                with patch('colcon_core.shell.logger.warning') as warn:
                    prefix_path = get_colcon_prefix_path()
                assert prefix_path == [str(basepath)]
                assert warn.call_count == 0


def test_check_dependency_availability():
    with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
        prefix_path = Path(prefix_path)

        dependencies = OrderedDict()
        dependencies['pkgA'] = prefix_path

        # missing package
        with pytest.raises(RuntimeError) as e:
            check_dependency_availability(
                dependencies, script_filename='package.ext')
        assert len(dependencies) == 1
        assert 'Failed to find the following files:' in str(e.value)
        assert str(prefix_path / 'share' / 'pkgA' / 'package.ext') \
            in str(e.value)
        assert 'Check that the following packages have been built:' \
            in str(e.value)
        assert '- pkgA' in str(e.value)

        # package in workspace
        (prefix_path / 'share' / 'pkgA').mkdir(parents=True)
        (prefix_path / 'share' / 'pkgA' / 'package.ext').write_text('')
        check_dependency_availability(
            dependencies, script_filename='package.ext')
        assert len(dependencies) == 1

        # package in environment
        dependencies['pkgA'] = prefix_path / 'invalid'
        with patch(
            'colcon_core.shell.find_installed_packages_in_environment',
            side_effect=lambda: {'pkgA': prefix_path / 'env'}
        ):
            with patch('colcon_core.shell.logger.warning') as warn:
                check_dependency_availability(
                    dependencies, script_filename='package.ext')
        assert len(dependencies) == 0
        assert warn.call_count == 1
        assert len(warn.call_args[0]) == 1
        assert warn.call_args[0][0].startswith(
            "The following packages are in the workspace but haven't been "
            'built:')
        assert '- pkgA' in warn.call_args[0][0]
        assert 'They are being used from the following locations instead:' \
            in warn.call_args[0][0]
        assert str(prefix_path / 'env') in warn.call_args[0][0]
        assert '--packages-ignore pkgA' in warn.call_args[0][0]


def test_find_installed_packages_in_environment():
    with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
        prefix_path = Path(prefix_path)
        prefix_path1 = prefix_path / 'one'
        prefix_path2 = prefix_path / 'two'

        with patch(
            'colcon_core.shell.get_chained_prefix_path',
            return_value=[prefix_path1, prefix_path2]
        ):
            # not used prefixes result debug messages
            with patch('colcon_core.shell.logger.debug') as debug:
                find_installed_packages_in_environment()
            assert debug.call_count == 2

            # the package is picked up from the first prefix
            with patch(
                'colcon_core.shell.find_installed_packages',
                side_effect=lambda p: {'pkgA': p}
            ):
                packages = find_installed_packages_in_environment()
        assert len(packages) == 1
        assert 'pkgA' in packages
        assert packages['pkgA'] == prefix_path1


def test_find_installed_packages():
    with TemporaryDirectory(prefix='test_colcon_') as install_base:
        install_base = Path(install_base)

        # install base doesn't exist
        assert find_installed_packages(install_base) is None

        # unknown install layout
        marker_file = install_base / '.colcon_install_layout'
        marker_file.write_text('unknown')
        assert find_installed_packages(install_base) is None

        # package index directory doesn't exist
        marker_file.write_text('merged')
        packages = find_installed_packages(install_base)
        assert len(packages) == 0

        with patch(
            'colcon_core.shell.get_relative_package_index_path',
            return_value=Path('relative/package/index')
        ) as rel_path:
            # setup for isolated case
            (install_base / 'dummy_file').write_text('')
            (install_base / '.hidden_dir').mkdir()
            (install_base / 'dummy_dir' / rel_path() / 'dummy_dir').mkdir(
                parents=True)
            (install_base / 'pkgA' / rel_path()).mkdir(parents=True)
            (install_base / 'pkgA' / rel_path() / 'pkgA').write_text('')

            # setup for merged case
            (install_base / rel_path() / 'dummy_dir').mkdir(parents=True)
            (install_base / rel_path() / '.dummy').write_text('')
            (install_base / rel_path() / 'pkgB').write_text('')
            (install_base / rel_path() / 'pkgC').write_text('')

            marker_file.write_text('isolated')
            packages = find_installed_packages(install_base)
            assert len(packages) == 1
            assert 'pkgA' in packages.keys()
            assert packages['pkgA'] == install_base / 'pkgA'

            marker_file.write_text('merged')
            packages = find_installed_packages(install_base)
            assert len(packages) == 2
            assert 'pkgB' in packages.keys()
            assert packages['pkgC'] == install_base
            assert 'pkgC' in packages.keys()
            assert packages['pkgB'] == install_base
