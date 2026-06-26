# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Tests for PEP 517 build task execution."""

import asyncio
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.python_project.distribution import _get_install_path
import colcon_core.shell
from colcon_core.shell.bat import BatShell
from colcon_core.shell.sh import ShShell
from colcon_core.subprocess import new_event_loop
from colcon_core.task import TaskContext
from colcon_core.task.python.build import PythonBuildTask
import pytest


@pytest.fixture(autouse=True)
def monkey_patch_get_shell_extensions(monkeypatch):
    """
    Fixture to monkeypatch shell extensions for the test context.

    :param monkeypatch: pytest monkeypatch fixture
    """
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
    """
    Fixture to monkeypatch TaskContext event queue method.

    :param monkeypatch: pytest monkeypatch fixture
    """
    monkeypatch.setattr(
        TaskContext, 'put_event_into_queue', lambda *args: None
    )


def test_build_pep517_package(tmp_path):
    """
    Test building a standard PEP 517 package using build_wheel.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    # Set up the dummy project
    src_dir = tmp_path / 'src'
    src_dir.mkdir(parents=True)

    # Write pyproject.toml
    pyproject_toml = src_dir / 'pyproject.toml'
    pyproject_toml.write_text(
        '[build-system]\n'
        'requires = ["setuptools>=40.8.0", "wheel"]\n'
        'build-backend = "setuptools.build_meta"\n'
        '\n'
        '[project]\n'
        'name = "test-pep517-pkg"\n'
        'version = "0.0.0"\n',
        encoding='utf-8'
    )

    # Create module directory and files
    module_dir = src_dir / 'test_pep517_pkg'
    module_dir.mkdir()
    (module_dir / '__init__.py').write_text(
        'def main(): pass\n', encoding='utf-8'
    )

    # Create package descriptor
    package = PackageDescriptor(src_dir)
    package.name = 'test-pep517-pkg'
    package.type = 'python'

    # Create TaskContext
    context = TaskContext(
        pkg=package,
        args=SimpleNamespace(
            path=str(src_dir),
            build_base=str(tmp_path / 'build'),
            install_base=str(tmp_path / 'install'),
            symlink_install=False,
        ),
        dependencies={}
    )

    python_build_task = PythonBuildTask()
    python_build_task.set_context(context=context)

    event_loop = new_event_loop()
    asyncio.set_event_loop(event_loop)
    try:
        rc = event_loop.run_until_complete(python_build_task.build())
        assert not rc

        # Verify build outputs
        install_base = tmp_path / 'install'
        libdir = Path(_get_install_path('purelib', install_base))
        assert (libdir / 'test_pep517_pkg' / '__init__.py').is_file()

        # Verify RECORD exists
        dist_infos = list(libdir.glob('test_pep517_pkg-*.dist-info'))
        assert len(dist_infos) == 1
        assert (dist_infos[0] / 'RECORD').is_file()
        assert (dist_infos[0] / 'INSTALLER').is_file()
    finally:
        event_loop.close()


def test_build_pep517_package_symlink(tmp_path):
    """
    Test building an editable PEP 517 package using build_editable.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    # Set up the dummy project
    src_dir = tmp_path / 'src'
    src_dir.mkdir(parents=True)

    # Write pyproject.toml
    pyproject_toml = src_dir / 'pyproject.toml'
    pyproject_toml.write_text(
        '[build-system]\n'
        'requires = ["setuptools>=61.0.0", "wheel"]\n'
        'build-backend = "setuptools.build_meta"\n'
        '\n'
        '[project]\n'
        'name = "test-pep517-pkg-symlink"\n'
        'version = "0.0.0"\n',
        encoding='utf-8'
    )

    # Create module directory and files
    module_dir = src_dir / 'test_pep517_pkg_symlink'
    module_dir.mkdir()
    (module_dir / '__init__.py').write_text(
        'def main(): pass\n', encoding='utf-8'
    )

    # Create package descriptor
    package = PackageDescriptor(src_dir)
    package.name = 'test-pep517-pkg-symlink'
    package.type = 'python'

    # Create TaskContext
    context = TaskContext(
        pkg=package,
        args=SimpleNamespace(
            path=str(src_dir),
            build_base=str(tmp_path / 'build'),
            install_base=str(tmp_path / 'install'),
            symlink_install=True,
        ),
        dependencies={}
    )

    python_build_task = PythonBuildTask()
    python_build_task.set_context(context=context)

    event_loop = new_event_loop()
    asyncio.set_event_loop(event_loop)
    try:
        rc = event_loop.run_until_complete(python_build_task.build())
        assert not rc

        # Verify build outputs
        install_base = tmp_path / 'install'
        libdir = Path(_get_install_path('purelib', install_base))

        dist_infos = list(libdir.glob('test_pep517_pkg_symlink-*.dist-info'))
        assert len(dist_infos) == 1

        # Check direct_url.json exists since it's an editable install
        assert (dist_infos[0] / 'direct_url.json').is_file()
    finally:
        event_loop.close()
