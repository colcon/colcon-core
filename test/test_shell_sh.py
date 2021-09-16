# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from colcon_core import shell
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell.sh import ShShell
import pytest

from .run_until_complete import run_until_complete


def test_extension():
    use_all_shell_extensions = shell.use_all_shell_extensions
    shell.use_all_shell_extensions = True
    try:
        with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
            _test_extension(Path(prefix_path))
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

    # create_prefix_script
    extension.create_prefix_script(prefix_path, False)
    assert (prefix_path / 'local_setup.sh').exists()
    assert (prefix_path / '_local_setup_util_sh.py').exists()

    # create_package_script
    extension.create_package_script(
        prefix_path, 'pkg_name', [
            ('hookA.sh', '/some/path/hookA.sh'),
            ('hookB.other', '/some/path/hookB.other')])
    assert (prefix_path / 'share' / 'pkg_name' / 'package.sh').exists()
    content = (prefix_path / 'share' / 'pkg_name' / 'package.sh').read_text()
    assert 'hookA' in content
    assert 'hookB' not in content

    # create_hook_append_value
    hook_path = extension.create_hook_append_value(
        'append_env_hook_name', prefix_path, 'pkg_name',
        'APPEND_NAME', 'append_subdirectory')
    assert hook_path.exists()
    assert hook_path.name == 'append_env_hook_name.sh'
    content = hook_path.read_text()
    assert 'APPEND_NAME' in content

    # create_hook_prepend_value
    hook_path = extension.create_hook_prepend_value(
        'env_hook_name', prefix_path, 'pkg_name', 'NAME', 'subdirectory')
    assert hook_path.exists()
    assert hook_path.name == 'env_hook_name.sh'
    content = hook_path.read_text()
    assert 'NAME' in content

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
            '- {prefix_path}/share/dep/package.sh\n'
            'Check that the following packages have been built:\n'
            '- dep'.format_map(locals()))

        # dependency script exists
        dep_script = prefix_path / 'share' / 'dep' / 'package.sh'
        os.makedirs(str(dep_script.parent))
        dep_script.write_text('')
        coroutine = extension.generate_command_environment(
            'task_name', prefix_path, {'dep': str(prefix_path)})
        env = run_until_complete(coroutine)
        assert isinstance(env, dict)
