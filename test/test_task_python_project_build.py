# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Tests for PythonProjectBuildTask."""

from subprocess import CalledProcessError
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

from colcon_core.event.output import StderrLine
from colcon_core.event.output import StdoutLine
from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.task import TaskContext
from colcon_core.task.python_project.build import PythonProjectBuildTask
import pytest


def test_task_init():
    """Test initialization of PythonProjectBuildTask."""
    task = PythonProjectBuildTask()
    assert task is not None


@pytest.mark.asyncio
async def test_build_task(tmp_path):
    """Test execution of PythonProjectBuildTask."""
    task = PythonProjectBuildTask()

    pkg_path = tmp_path / 'src' / 'pkg'
    pkg_path.mkdir(parents=True)
    (pkg_path / 'pyproject.toml').write_text(
        '[project]\nname = "my-pkg"\nversion = "0.1.0"\n'
    )
    (pkg_path / 'setup.cfg').write_text(
        '[install]\ninstall-scripts = $base/bin\n'
    )

    desc = PackageDescriptor(str(pkg_path))
    desc.name = 'my-pkg'
    desc.type = 'python.project'

    build_base = tmp_path / 'build'
    install_base = tmp_path / 'install'
    build_base.mkdir()
    install_base.mkdir()

    events = []
    context = TaskContext(
        pkg=desc,
        args=SimpleNamespace(
            path=str(pkg_path),
            build_base=str(build_base),
            install_base=str(install_base),
            symlink_install=False,
        ),
        dependencies={},
    )
    context.put_event_into_queue = lambda ev: events.append(ev)
    task.set_context(context=context)

    mock_hook_caller = MagicMock()
    mock_whl = 'my_pkg-0.1.0-py3-none-any.whl'
    mock_hook_caller.call_hook = AsyncMock(return_value=mock_whl)
    dist_info_dir = install_base / 'my_pkg-0.1.0.dist-info'
    dist_info_dir.mkdir(parents=True)
    (dist_info_dir / 'RECORD').write_text('')

    target_env = (
        'colcon_core.task.python_project.build.get_command_environment'
    )
    target_hook = (
        'colcon_core.task.python_project.build.get_decorated_hook_caller'
    )
    target_wheel = (
        'colcon_core.task.python_project.build.install_wheel'
    )

    def fake_get_hook_caller(pkg, **kwargs):
        if 'stdout_callback' in kwargs and kwargs['stdout_callback']:
            kwargs['stdout_callback']('sample stdout')
        if 'stderr_callback' in kwargs and kwargs['stderr_callback']:
            kwargs['stderr_callback']('sample stderr')
        return mock_hook_caller

    with patch(
        target_env,
        new_callable=AsyncMock,
        return_value={}
    ), patch(
        target_hook,
        side_effect=fake_get_hook_caller
    ), patch(
        target_wheel,
        return_value=dist_info_dir
    ):
        result = await task.build()
        assert result is None
        assert mock_hook_caller.call_hook.called
        assert any(isinstance(e, StdoutLine) for e in events)
        assert any(isinstance(e, StderrLine) for e in events)


@pytest.mark.asyncio
async def test_build_task_symlink_install(tmp_path):
    """Test execution of PythonProjectBuildTask with --symlink-install."""
    task = PythonProjectBuildTask()

    pkg_path = tmp_path / 'src' / 'pkg'
    pkg_path.mkdir(parents=True)
    (pkg_path / 'pyproject.toml').write_text(
        '[project]\nname = "my-pkg"\nversion = "0.1.0"\n'
    )
    (pkg_path / 'setup.cfg').write_text(
        '[develop]\nscript-dir = $base/bin\n'
    )

    desc = PackageDescriptor(str(pkg_path))
    desc.name = 'my-pkg'
    desc.type = 'python.project'

    build_base = tmp_path / 'build'
    install_base = tmp_path / 'install'
    build_base.mkdir()
    install_base.mkdir()

    context = TaskContext(
        pkg=desc,
        args=SimpleNamespace(
            path=str(pkg_path),
            build_base=str(build_base),
            install_base=str(install_base),
            symlink_install=True,
        ),
        dependencies={},
    )
    task.set_context(context=context)

    mock_hook_caller = MagicMock()
    mock_hook_caller.list_hooks = AsyncMock(return_value=['build_editable'])
    mock_whl = 'my_pkg-0.1.0-py3-none-any.whl'
    mock_hook_caller.call_hook = AsyncMock(return_value=mock_whl)
    dist_info_dir = install_base / 'my_pkg-0.1.0.dist-info'
    dist_info_dir.mkdir(parents=True)
    (dist_info_dir / 'RECORD').write_text('')

    target_env = (
        'colcon_core.task.python_project.build.get_command_environment'
    )
    target_hook = (
        'colcon_core.task.python_project.build.get_decorated_hook_caller'
    )
    target_wheel = (
        'colcon_core.task.python_project.build.install_wheel'
    )
    with patch(
        target_env,
        new_callable=AsyncMock,
        return_value={}
    ), patch(
        target_hook,
        return_value=mock_hook_caller
    ), patch(
        target_wheel,
        return_value=dist_info_dir
    ):
        result = await task.build()
        assert result is None
        assert (dist_info_dir / 'direct_url.json').is_file()


@pytest.mark.asyncio
async def test_build_task_error(tmp_path):
    """Test PythonProjectBuildTask failure handling."""
    task = PythonProjectBuildTask()

    pkg_path = tmp_path / 'src' / 'pkg'
    pkg_path.mkdir(parents=True)

    desc = PackageDescriptor(str(pkg_path))
    desc.name = 'my-pkg'
    desc.type = 'python.project'

    build_base = tmp_path / 'build'
    install_base = tmp_path / 'install'
    build_base.mkdir()
    install_base.mkdir()

    context = TaskContext(
        pkg=desc,
        args=SimpleNamespace(
            path=str(pkg_path),
            build_base=str(build_base),
            install_base=str(install_base),
            symlink_install=False,
        ),
        dependencies={},
    )
    task.set_context(context=context)

    mock_hook_caller = MagicMock()
    err = CalledProcessError(2, ['cmd'])
    mock_hook_caller.call_hook = AsyncMock(side_effect=err)

    target_env = (
        'colcon_core.task.python_project.build.get_command_environment'
    )
    target_hook = (
        'colcon_core.task.python_project.build.get_decorated_hook_caller'
    )
    with patch(
        target_env,
        new_callable=AsyncMock,
        return_value={}
    ), patch(
        target_hook,
        return_value=mock_hook_caller
    ):
        result = await task.build()
        assert result == 2
