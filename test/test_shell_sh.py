# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from colcon_core import shell
from colcon_core.location import get_relative_package_index_path
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell import get_environment_variables
from colcon_core.shell import get_null_separated_environment_variables
from colcon_core.shell.dsv import DsvShell
from colcon_core.shell.sh import ShShell
import pytest

from .run_until_complete import run_until_complete


def test_extension():
    use_all_shell_extensions = shell.use_all_shell_extensions
    shell.use_all_shell_extensions = True
    try:
        with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
            _test_extension(Path(prefix_path))
            _test_prefix_script(Path(prefix_path))
    finally:
        shell.use_all_shell_extensions = use_all_shell_extensions

    if sys.platform == 'win32':
        shell.use_all_shell_extensions = False
        try:
            with pytest.raises(SkipExtensionException):
                ShShell()
        finally:
            shell.use_all_shell_extensions = use_all_shell_extensions


def _test_extension(prefix_path):
    extension = ShShell()

    # create_hook_append_value
    append_hook_path = extension.create_hook_append_value(
        'append_env_hook_name', prefix_path, 'pkg_name',
        'APPEND_NAME', 'subdirectory')
    assert append_hook_path.exists()
    assert append_hook_path.name == 'append_env_hook_name.sh'
    content = append_hook_path.read_text()
    assert 'APPEND_NAME' in content

    # create_hook_prepend_value
    prepend_hook_path = extension.create_hook_prepend_value(
        'prepend_env_hook_name', prefix_path, 'pkg_name',
        'PREPEND_NAME', 'subdirectory')
    assert prepend_hook_path.exists()
    assert prepend_hook_path.name == 'prepend_env_hook_name.sh'
    content = prepend_hook_path.read_text()
    assert 'PREPEND_NAME' in content

    # create_package_script
    extension.create_package_script(
        prefix_path, 'pkg_name', [
            (append_hook_path.relative_to(prefix_path), ()),
            (prepend_hook_path.relative_to(prefix_path), ()),
            ('hookB.other', '/some/path/hookB.other')])
    assert (prefix_path / 'share' / 'pkg_name' / 'package.sh').exists()
    content = (prefix_path / 'share' / 'pkg_name' / 'package.sh').read_text()
    assert append_hook_path.name in content
    assert prepend_hook_path.name in content
    assert 'hookB' not in content

    # generate_command_environment
    if sys.platform == 'win32':
        with pytest.raises(SkipExtensionException) as e:
            coroutine = extension.generate_command_environment(
                'task_name', prefix_path, {})
            run_until_complete(coroutine)
        assert str(e.value).endswith('Not usable on Windows systems')
    else:
        # dependency script missing
        with pytest.raises(RuntimeError) as e:
            coroutine = extension.generate_command_environment(
                'task_name', prefix_path, {'dep': str(prefix_path)})
            run_until_complete(coroutine)
        assert str(e.value) == (
            'Failed to find the following files:\n'
            f'- {prefix_path}/share/dep/package.sh\n'
            'Check that the following packages have been built:\n'
            '- dep')

        # dependency script exists
        dep_script = prefix_path / 'share' / 'dep' / 'package.sh'
        os.makedirs(str(dep_script.parent))
        dep_script.write_text('')
        coroutine = extension.generate_command_environment(
            'task_name', prefix_path, {'dep': str(prefix_path)})
        env = run_until_complete(coroutine)
        assert isinstance(env, dict)

        subdirectory_path = str(prefix_path / 'subdirectory')

        # validate appending/prepending without existing values
        with patch.dict(os.environ) as env_patch:
            env_patch.pop('APPEND_NAME', None)
            env_patch.pop('PREPEND_NAME', None)
            coroutine = extension.generate_command_environment(
                'task_name', prefix_path, {'pkg_name': str(prefix_path)})
            env = run_until_complete(coroutine)
            assert env.get('APPEND_NAME') == subdirectory_path
            assert env.get('PREPEND_NAME') == subdirectory_path

        # validate appending/prepending with existing values
        with patch.dict(os.environ, {
            'APPEND_NAME': 'control',
            'PREPEND_NAME': 'control',
        }):
            coroutine = extension.generate_command_environment(
                'task_name', prefix_path, {'pkg_name': str(prefix_path)})
            env = run_until_complete(coroutine)
            # Expect excess separators to be removed
            assert env.get('APPEND_NAME') == os.pathsep.join((
                'control',
                subdirectory_path,
            ))
            # Expect excess separators to be removed
            assert env.get('PREPEND_NAME') == os.pathsep.join((
                subdirectory_path,
                'control',
            ))

        # validate appending/prepending unique values
        with patch.dict(os.environ, {
            'APPEND_NAME': os.pathsep.join((subdirectory_path, 'control')),
            'PREPEND_NAME': os.pathsep.join(('control', subdirectory_path)),
        }):
            coroutine = extension.generate_command_environment(
                'task_name', prefix_path, {'pkg_name': str(prefix_path)})
            env = run_until_complete(coroutine)
            # Expect no change, value already appears earlier in the list
            assert env.get('APPEND_NAME') == os.pathsep.join((
                subdirectory_path,
                'control',
            ))
            # Expect value to be *moved* to the front of the list
            assert env.get('PREPEND_NAME') == os.pathsep.join((
                subdirectory_path,
                'control',
            ))


async def _run_prefix_script(prefix_script):
    # Attempt to use null-separated env output, but fall back to the
    # best-effort implementation if not supported (i.e. older macOS)
    cmd = ['.', str(prefix_script), '&&', 'env', '-0']
    try:
        return await get_null_separated_environment_variables(cmd)
    except AssertionError:
        cmd.pop()
        return await get_environment_variables(cmd)


def _test_prefix_script(prefix_path):
    extension = ShShell()

    # ShShell requires the (non-primary) DsvShell extension as well
    dsv_extension = DsvShell()

    # create_hook_append_value
    append_hook_path = dsv_extension.create_hook_append_value(
        'append_env_hook_name', prefix_path, 'pkg_name',
        'APPEND_NAME', 'subdirectory')
    assert append_hook_path.exists()
    assert append_hook_path.name == 'append_env_hook_name.dsv'
    content = append_hook_path.read_text()
    assert 'APPEND_NAME' in content

    # create_hook_prepend_value
    prepend_hook_path = dsv_extension.create_hook_prepend_value(
        'prepend_env_hook_name', prefix_path, 'pkg_name',
        'PREPEND_NAME', 'subdirectory')
    assert prepend_hook_path.exists()
    assert prepend_hook_path.name == 'prepend_env_hook_name.dsv'
    content = prepend_hook_path.read_text()
    assert 'PREPEND_NAME' in content

    # mark package as installed
    package_index = prefix_path / get_relative_package_index_path()
    package_index.mkdir(parents=True)
    (package_index / 'pkg_name').write_text('')

    # create_package_script
    dsv_extension.create_package_script(
        prefix_path, 'pkg_name', [
            (append_hook_path.relative_to(prefix_path), ()),
            (prepend_hook_path.relative_to(prefix_path), ())])
    assert (prefix_path / 'share' / 'pkg_name' / 'package.dsv').exists()
    content = (prefix_path / 'share' / 'pkg_name' / 'package.dsv').read_text()
    assert append_hook_path.name in content
    assert prepend_hook_path.name in content

    # create_prefix_script
    extension.create_prefix_script(prefix_path, True)
    prefix_script = prefix_path / 'local_setup.sh'
    prefix_script.exists()
    assert (prefix_path / '_local_setup_util_sh.py').exists()

    if sys.platform != 'win32':
        subdirectory_path = str(prefix_path / 'subdirectory')

        # validate appending/prepending without existing values
        with patch.dict(os.environ, {
            'APPEND_NAME': '',
            'PREPEND_NAME': '',
        }):
            coroutine = _run_prefix_script(prefix_script)
            env = run_until_complete(coroutine)
            assert env.get('APPEND_NAME') == subdirectory_path
            assert env.get('PREPEND_NAME') == subdirectory_path

        # validate appending/prepending with existing values
        with patch.dict(os.environ, {
            'APPEND_NAME': 'control',
            'PREPEND_NAME': 'control',
        }):
            coroutine = _run_prefix_script(prefix_script)
            env = run_until_complete(coroutine)
            assert env.get('APPEND_NAME') == os.pathsep.join((
                'control',
                subdirectory_path,
            ))
            assert env.get('PREPEND_NAME') == os.pathsep.join((
                subdirectory_path,
                'control',
            ))

        # validate appending/prepending unique values
        with patch.dict(os.environ, {
            'APPEND_NAME': os.pathsep.join((subdirectory_path, 'control')),
            'PREPEND_NAME': os.pathsep.join(('control', subdirectory_path)),
        }):
            coroutine = _run_prefix_script(prefix_script)
            env = run_until_complete(coroutine)
            # Expect no change, value already appears earlier in the list
            assert env.get('APPEND_NAME') == os.pathsep.join((
                subdirectory_path,
                'control',
            ))
            # TODO: The DsvShell behavior doesn't align with ShShell!
            # ~~Expect value to be *moved* to the front of the list~~
            assert env.get('PREPEND_NAME') == os.pathsep.join((
                'control',
                subdirectory_path,
            ))
