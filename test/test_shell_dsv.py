# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from unittest.mock import patch

from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell.dsv import DsvShell
import pytest

from .run_until_complete import run_until_complete


def _write_package_descriptor(prefix_path, pkg_name, lines):
    descriptor = prefix_path / 'share' / pkg_name / 'package.dsv'
    descriptor.parent.mkdir(parents=True, exist_ok=True)
    descriptor.write_text(''.join(f'{line}\n' for line in lines))
    return descriptor


def _generate_command_environment(prefix_path, pkg_name):
    extension = DsvShell()
    coroutine = extension.generate_command_environment(
        'task_name', prefix_path, {pkg_name: str(prefix_path)})
    return run_until_complete(coroutine)


def test_extension(tmp_path):
    extension = DsvShell()

    # create_prefix_script
    assert extension.create_prefix_script(tmp_path, True) == []

    # create_hook_append_value
    append_hook_path = extension.create_hook_append_value(
        'append_env_hook_name', tmp_path, 'pkg_name',
        'APPEND_NAME', 'subdirectory')
    assert append_hook_path.exists()
    assert append_hook_path.name == 'append_env_hook_name.dsv'
    assert 'APPEND_NAME' in append_hook_path.read_text()

    # create_hook_prepend_value
    prepend_hook_path = extension.create_hook_prepend_value(
        'prepend_env_hook_name', tmp_path, 'pkg_name',
        'PREPEND_NAME', 'subdirectory')
    assert prepend_hook_path.exists()
    assert prepend_hook_path.name == 'prepend_env_hook_name.dsv'
    assert 'PREPEND_NAME' in prepend_hook_path.read_text()

    # create_hook_set_value
    set_hook_path = extension.create_hook_set_value(
        'set_env_hook_name', tmp_path, 'pkg_name', 'SET_NAME', 'value')
    assert set_hook_path.exists()
    assert set_hook_path.name == 'set_env_hook_name.dsv'
    assert 'SET_NAME' in set_hook_path.read_text()

    # create_package_script
    extension.create_package_script(
        tmp_path, 'pkg_name', [
            (append_hook_path.relative_to(tmp_path), ()),
            (prepend_hook_path.relative_to(tmp_path), ()),
            (set_hook_path.relative_to(tmp_path), ())])
    descriptor = tmp_path / 'share' / 'pkg_name' / 'package.dsv'
    assert descriptor.exists()
    content = descriptor.read_text()
    assert append_hook_path.name in content
    assert prepend_hook_path.name in content
    assert set_hook_path.name in content


def test_generate_command_environment(tmp_path):
    extension = DsvShell()

    # dependency descriptor missing, a shell extension needs to take over
    with pytest.raises(SkipExtensionException) as e:
        coroutine = extension.generate_command_environment(
            'task_name', tmp_path, {'dep': str(tmp_path)})
        run_until_complete(coroutine)
    assert str(e.value) == 'Not all dependencies provide a descriptor'

    # dependency descriptor exists
    _write_package_descriptor(tmp_path, 'dep', [])
    with patch.dict(os.environ, {'CONTROL_NAME': 'control'}):
        env = _generate_command_environment(tmp_path, 'dep')
    assert isinstance(env, dict)
    assert env.get('CONTROL_NAME') == 'control'

    # the environment is written for debugging
    env_path = tmp_path / 'colcon_command_prefix_task_name.dsv.env'
    assert 'CONTROL_NAME=control' in env_path.read_text().splitlines()

    # the build base doesn't exist yet in a clean build
    build_base = tmp_path / 'build' / 'dep'
    coroutine = extension.generate_command_environment(
        'task_name', build_base, {'dep': str(tmp_path)})
    run_until_complete(coroutine)
    assert (build_base / 'colcon_command_prefix_task_name.dsv.env').exists()


def test_generate_command_environment_values(tmp_path):
    subdirectory_path = str(tmp_path / 'subdirectory')
    _write_package_descriptor(tmp_path, 'pkg_name', [
        'append-non-duplicate;APPEND_NAME;subdirectory',
        'prepend-non-duplicate;PREPEND_NAME;subdirectory',
    ])

    # validate appending/prepending without existing values
    with patch.dict(os.environ) as env_patch:
        env_patch.pop('APPEND_NAME', None)
        env_patch.pop('PREPEND_NAME', None)
        env = _generate_command_environment(tmp_path, 'pkg_name')
    assert env.get('APPEND_NAME') == subdirectory_path
    assert env.get('PREPEND_NAME') == subdirectory_path

    # validate appending/prepending with existing values
    with patch.dict(os.environ, {
        'APPEND_NAME': 'control',
        'PREPEND_NAME': 'control',
    }):
        env = _generate_command_environment(tmp_path, 'pkg_name')
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
        env = _generate_command_environment(tmp_path, 'pkg_name')
    # Expect no change, value already appears in the list
    assert env.get('APPEND_NAME') == os.pathsep.join((
        subdirectory_path,
        'control',
    ))
    # Expect no change either, the descriptors are being evaluated like the
    # `prefix_util.py` template does, which skips duplicates instead of moving
    # them to the front of the list like the shell specific hook scripts do
    assert env.get('PREPEND_NAME') == os.pathsep.join((
        'control',
        subdirectory_path,
    ))


def test_generate_command_environment_types(tmp_path):
    (tmp_path / 'subdirectory').mkdir()
    _write_package_descriptor(tmp_path, 'pkg_name', [
        '# a comment',
        '',
        'set;SET_NAME;subdirectory',
        'set;SET_OTHER_NAME;not-a-path',
        'set-if-unset;SET_IF_UNSET_NAME;value',
        'set-if-unset;CONTROL_NAME;value',
        'prepend-non-duplicate-if-exists;IF_EXISTS_NAME;subdirectory',
        'prepend-non-duplicate-if-exists;IF_EXISTS_NAME;other-subdirectory',
    ])

    with patch.dict(os.environ, {'CONTROL_NAME': 'control'}):
        env = _generate_command_environment(tmp_path, 'pkg_name')

    # a value which is a path relative to the prefix is being expanded
    assert env.get('SET_NAME') == str(tmp_path / 'subdirectory')
    assert env.get('SET_OTHER_NAME') == 'not-a-path'
    assert env.get('SET_IF_UNSET_NAME') == 'value'
    assert env.get('CONTROL_NAME') == 'control'
    # only the existing path is being prepended
    assert env.get('IF_EXISTS_NAME') == str(tmp_path / 'subdirectory')

    # an unknown type is an error
    _write_package_descriptor(
        tmp_path, 'pkg_name', ['unknown-type;NAME;value'])
    with pytest.raises(RuntimeError) as e:
        _generate_command_environment(tmp_path, 'pkg_name')
    assert 'unknown environment hook type' in str(e.value)

    # a line without a semicolon is an error
    _write_package_descriptor(tmp_path, 'pkg_name', ['no-semicolon'])
    with pytest.raises(RuntimeError) as e:
        _generate_command_environment(tmp_path, 'pkg_name')
    assert 'semicolon separating the type' in str(e.value)


def test_generate_command_environment_recursion(tmp_path):
    hook_path = tmp_path / 'share' / 'pkg_name' / 'hook' / 'hook_name.dsv'
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text('set;SET_NAME;value\n')
    _write_package_descriptor(tmp_path, 'pkg_name', [
        # scripts of other shells are only considered by their descriptor
        'source;share/pkg_name/hook/hook_name.ext',
        'source;share/pkg_name/hook/hook_name.dsv',
        # a basename without any descriptor or known script is being ignored
        'source;share/pkg_name/hook/other_hook_name.marker',
    ])

    with patch(
        'colcon_core.shell.dsv._get_script_extensions', return_value={'ext'}
    ):
        env = _generate_command_environment(tmp_path, 'pkg_name')
    assert env.get('SET_NAME') == 'value'

    # a script of another shell without a descriptor can't be evaluated
    _write_package_descriptor(tmp_path, 'pkg_name', [
        'source;share/pkg_name/hook/script_only.ext',
    ])
    with patch(
        'colcon_core.shell.dsv._get_script_extensions', return_value={'ext'}
    ):
        with pytest.raises(SkipExtensionException) as e:
            _generate_command_environment(tmp_path, 'pkg_name')
    assert 'script_only.ext' in str(e.value)
