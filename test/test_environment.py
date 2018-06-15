# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.environment import create_environment_hooks
from colcon_core.environment import create_environment_scripts
from colcon_core.environment import EnvironmentExtensionPoint
from colcon_core.environment import get_environment_extensions
from colcon_core.shell import get_shell_extensions
from colcon_core.shell import ShellExtensionPoint
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


def test_extension_interface():
    extension = EnvironmentExtensionPoint()
    with pytest.raises(NotImplementedError):
        extension.create_environment_hooks(None, None)


class Extension1(EnvironmentExtensionPoint):

    def create_environment_hooks(self, prefix_path, pkg_name):
        return [
            '{prefix_path}/share/{pkg_name}/hook/one.ext'.format_map(locals()),
            '{prefix_path}/share/{pkg_name}/hook/two.ext'.format_map(locals()),
        ]


class Extension2(EnvironmentExtensionPoint):
    PRIORITY = 110


def test_get_environment_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_environment_extensions()
    assert list(extensions.keys()) == ['extension2', 'extension1']


class Extension3(ShellExtensionPoint):
    pass


class Extension4(ShellExtensionPoint):
    pass


def test_create_environment_scripts():
    with TemporaryDirectory(prefix='test_colcon_') as basepath:
        pkg = Mock()
        pkg.name = 'name'
        pkg.dependencies = {}
        pkg.hooks = []
        args = Mock()
        args.install_base = basepath

        # no hooks at all
        with patch(
            'colcon_core.environment.create_environment_hooks', return_value=[]
        ):
            with patch(
                'colcon_core.environment.get_shell_extensions', return_value={}
            ):
                create_environment_scripts(pkg, args)

        pkg.hooks = [os.path.join(basepath, 'subA')]
        with EntryPointContext(extension3=Extension3, extension4=Extension4):
            extensions = get_shell_extensions()
            # one invalid return value, one check correct hooks argument
            extensions[100]['extension3'].create_package_script = Mock()
            extensions[100]['extension4'].create_package_script = Mock(
                return_value=None)
            with patch('colcon_core.environment.logger.error') as error:
                create_environment_scripts(
                    pkg, args, default_hooks=[('subB', )],
                    additional_hooks=[['subC', 'arg1', 'arg2']])
            # the raised exception is catched and results in an error message
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in shell extension 'extension3': "
                'create_package_script() should return None\n')
            # check for correct hooks argument
            mock = extensions[100]['extension4'].create_package_script
            assert mock.call_count == 1
            assert len(mock.call_args[0]) == 3
            assert mock.call_args[0][0] == Path(args.install_base)
            assert mock.call_args[0][1] == pkg.name
            hook_tuples = mock.call_args[0][2]
            assert len(hook_tuples) == 3
            assert hook_tuples[0] == ('subB', ())
            assert hook_tuples[1] == ('subC', ['arg1', 'arg2'])
            assert hook_tuples[2] == ('subA', [])


def test_create_environment_hooks():
    with TemporaryDirectory(prefix='test_colcon_') as basepath:
        with EntryPointContext(extension1=Extension1, extension2=Extension2):
            with patch('colcon_core.environment.logger.error') as error:
                hooks = create_environment_hooks(basepath, 'pkg_name')
    assert len(hooks) == 2
    assert hooks[0] == '{basepath}/share/pkg_name/hook/one.ext' \
        .format_map(locals())
    assert hooks[1] == '{basepath}/share/pkg_name/hook/two.ext' \
        .format_map(locals())
    # the raised exception is catched and results in an error message
    assert error.call_count == 1
    assert len(error.call_args[0]) == 1
    assert error.call_args[0][0].startswith(
        "Exception in environment extension 'extension2': \n")
