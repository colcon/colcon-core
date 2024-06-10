# Copyright 2019 Rover Robotics
# Licensed under the Apache License, Version 2.0

import asyncio
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.plugin_system import SkipExtensionException
import colcon_core.shell
from colcon_core.shell.bat import BatShell
from colcon_core.shell.sh import ShShell
from colcon_core.subprocess import new_event_loop
from colcon_core.task import TaskContext
from colcon_core.task.python.build import PythonBuildTask
import pytest


@pytest.fixture(autouse=True)
def monkey_patch_get_shell_extensions(monkeypatch):
    a_shell = None
    for shell_extension_class in [ShShell, BatShell]:
        with suppress(SkipExtensionException):
            a_shell = shell_extension_class()
            break

    if a_shell is None:
        pytest.fail('No valid shell extension found.')

    monkeypatch.setattr(
        colcon_core.shell,
        'get_shell_extensions',
        lambda: {
            200: {'mock': a_shell}
        }
    )


@pytest.fixture(autouse=True)
def monkey_patch_put_event_into_queue(monkeypatch):
    monkeypatch.setattr(
        TaskContext, 'put_event_into_queue', lambda *args: None
    )


def _test_build_package(
    tmp_path_str, *, symlink_install, setup_cfg, libexec_pattern, data_files
):
    assert not libexec_pattern or setup_cfg, \
        'The libexec pattern requires use of setup.cfg'

    if setup_cfg and data_files:
        pytest.importorskip('setuptools', minversion='40.5.0')

    event_loop = new_event_loop()
    asyncio.set_event_loop(event_loop)
    try:
        tmp_path = Path(tmp_path_str)
        python_build_task = PythonBuildTask()
        package = PackageDescriptor(tmp_path / 'src')
        package.name = 'test-package'
        package.type = 'python'
        package.metadata['get_python_setup_options'] = lambda _: {
            'packages': ['my_module'],
            **(
                {
                    'data_files': [
                        ('share/test_package', ['test-resource']),
                    ]
                } if data_files else {}
            )
        }

        context = TaskContext(
            pkg=package,
            args=SimpleNamespace(
                path=str(tmp_path / 'src'),
                build_base=str(tmp_path / 'build'),
                install_base=str(tmp_path / 'install'),
                symlink_install=symlink_install,
            ),
            dependencies={}
        )
        python_build_task.set_context(context=context)

        pkg = python_build_task.context.pkg

        pkg.path.mkdir(exist_ok=True)
        if setup_cfg:
            (pkg.path / 'setup.py').write_text(
                'from setuptools import setup\n'
                'setup()\n'
            )
            (pkg.path / 'setup.cfg').write_text(
                '[metadata]\n'
                'name = test-package\n'
                '[options]\n'
                'packages = find:\n'
                '[options.entry_points]\n'
                'console_scripts =\n'
                '    my_command = my_module:main\n'
                + (
                    '[develop]\n'
                    'script-dir=$base/lib/test_package\n'
                    '[install]\n'
                    'install-scripts=$base/lib/test_package\n'
                    if libexec_pattern else ''
                ) + (
                    '[options.data_files]\n'
                    'share/test_package = test-resource\n'
                    if data_files else ''
                )
            )
        else:
            (pkg.path / 'setup.py').write_text(
                'from setuptools import setup\n'
                'setup(\n'
                '    name="test-package",\n'
                '    packages=["my_module"],\n'
                '    entry_points={\n'
                '        "console_scripts": ["my_command = my_module:main"],\n'
                '    },\n'
                + (
                     '    data_files=[\n'
                     '        ("share/test_package", [\n'
                     '            "test-resource",\n'
                     '        ]),\n'
                     '    ],\n'
                     if data_files else ''
                ) +
                ')\n'
            )
        (pkg.path / 'my_module').mkdir(exist_ok=True)
        (pkg.path / 'test-resource').touch()
        (pkg.path / 'my_module' / '__init__.py').write_text(
            'def main():\n'
            '    print("Hello, World!")\n'
        )

        src_base = Path(python_build_task.context.args.path)

        source_files_before = set(src_base.rglob('*'))
        rc = event_loop.run_until_complete(python_build_task.build())
        assert not rc
        source_files_after = set(src_base.rglob('*'))
        assert source_files_before == source_files_after

        build_base = Path(python_build_task.context.args.build_base)
        assert build_base.rglob('my_module/__init__.py')

        install_base = Path(python_build_task.context.args.install_base)
        assert symlink_install == any(install_base.rglob(
            'test-package.egg-link'))
        assert symlink_install != any(install_base.rglob(
            'PKG-INFO'))
        assert libexec_pattern == any(install_base.rglob(
            'lib/test_package/my_command*'))
        assert libexec_pattern != (
            any(install_base.rglob('bin/my_command*')) or
            any(install_base.rglob('Scripts/my_command*')))
        assert data_files == any(install_base.rglob(
            'share/test_package/test-resource'))

        if not symlink_install:
            pkg_info, = install_base.rglob('PKG-INFO')
            assert 'Name: test-package' in pkg_info.read_text().splitlines()
    finally:
        event_loop.close()


@pytest.mark.parametrize(
    'data_files',
    [False, True])
@pytest.mark.parametrize(
    'setup_cfg,libexec_pattern',
    [(False, False), (True, False), (True, True)])
@pytest.mark.parametrize(
    'symlink_first',
    [False, True])
def test_build_package(symlink_first, setup_cfg, libexec_pattern, data_files):
    with TemporaryDirectory(prefix='test_colcon_') as tmp_path_str:
        _test_build_package(
            tmp_path_str, symlink_install=symlink_first,
            setup_cfg=setup_cfg, libexec_pattern=libexec_pattern,
            data_files=data_files)

        # Test again with the symlink flag inverted to validate cleanup
        _test_build_package(
            tmp_path_str, symlink_install=not symlink_first,
            setup_cfg=setup_cfg, libexec_pattern=libexec_pattern,
            data_files=data_files)
