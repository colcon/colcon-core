# Copyright 2019 Rover Robotics
# Licensed under the Apache License, Version 2.0

import asyncio
from pathlib import Path
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
        try:
            a_shell = shell_extension_class()
            break
        except SkipExtensionException:
            pass

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


@pytest.fixture
def python_build_task(tmp_path):
    task = PythonBuildTask()
    package = PackageDescriptor(tmp_path / 'src')
    package.name = 'test_package'
    package.type = 'python'

    context = TaskContext(
        pkg=package,
        args=SimpleNamespace(
            path=str(tmp_path / 'src'),
            build_base=str(tmp_path / 'build'),
            install_base=str(tmp_path / 'install'),
            symlink_install=False,
        ),
        dependencies={}
    )
    task.set_context(context=context)
    yield task


@pytest.fixture
def event_loop():
    loop = new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def test_build_package(python_build_task: PythonBuildTask, event_loop):
    pkg = python_build_task.context.pkg

    pkg.path.mkdir()
    (pkg.path / 'setup.py').write_text(
        'from setuptools import setup\n'
        'setup(\n'
        '    name="test_package",\n'
        '    packages=["my_module"],\n'
        ')\n'
    )
    (pkg.path / 'my_module').mkdir()
    (pkg.path / 'my_module' / '__init__.py').touch()

    src_base = Path(python_build_task.context.args.path)

    source_files_before = set(src_base.rglob('*'))
    event_loop.run_until_complete(python_build_task.build())
    source_files_after = set(src_base.rglob('*'))
    assert source_files_before == source_files_after

    build_base = Path(python_build_task.context.args.build_base)
    assert 1 == len(list(build_base.rglob('my_module/__init__.py')))

    install_base = Path(python_build_task.context.args.install_base)
    assert 1 == len(list(install_base.rglob('my_module/__init__.py')))

    pkg_info, = install_base.rglob('PKG-INFO')
    assert 'Name: test-package' in pkg_info.read_text().splitlines()
