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

from .run_until_complete import run_until_complete


def test_task_init():
    """Test initialization of PythonProjectBuildTask."""
    task = PythonProjectBuildTask()
    assert task is not None


def test_build_task(tmp_path):
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
        result = run_until_complete(task.build())
        assert result is None
        assert mock_hook_caller.call_hook.called
        assert any(isinstance(e, StdoutLine) for e in events)
        assert any(isinstance(e, StderrLine) for e in events)


def test_build_task_symlink_install(tmp_path):
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
        result = run_until_complete(task.build())
        assert result is None
        assert (dist_info_dir / 'direct_url.json').is_file()


def test_build_task_error(tmp_path):
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
        result = run_until_complete(task.build())
        assert result == 2


def test_get_data_files_mapping_by_backend(tmp_path):
    """Test backend-scoped data-files resolution across build backends."""
    task = PythonProjectBuildTask()
    pkg_path = tmp_path / 'src' / 'pkg'
    pkg_path.mkdir(parents=True)

    (pkg_path / 'pyproject.toml').write_text(
        '[project]\n'
        'name = "my-pkg"\n'
        'version = "0.1.0"\n'
        '[tool.setuptools.data-files]\n'
        '"share/my_pkg/launch" = ["launch/*.py"]\n'
        '[tool.hatch.build.targets.wheel.shared-data]\n'
        '"launch" = "share/my_pkg/launch"\n'
        '"config/app.yaml" = "share/my_pkg/config/app.yaml"\n'
    )
    (pkg_path / 'setup.cfg').write_text(
        '[options.data_files]\n'
        'share/my_pkg/extra = extra/info.txt\n'
    )
    (pkg_path / 'launch').mkdir()
    (pkg_path / 'launch' / 'node.py').write_text('NODE = 1\n')
    (pkg_path / 'config').mkdir()
    (pkg_path / 'config' / 'app.yaml').write_text('a: 1\n')
    (pkg_path / 'extra').mkdir()
    (pkg_path / 'extra' / 'info.txt').write_text('info\n')

    desc = PackageDescriptor(str(pkg_path))
    desc.name = 'my-pkg'
    desc.type = 'python.project'

    st_map = task._get_data_files_mapping(desc, 'setuptools.build_meta')
    assert st_map == {
        'extra/info.txt': 'share/my_pkg/extra/info.txt',
        'launch/node.py': 'share/my_pkg/launch/node.py',
    }

    hatch_map = task._get_data_files_mapping(desc, 'hatchling.build')
    assert hatch_map == {
        'launch/node.py': 'share/my_pkg/launch/node.py',
        'config/app.yaml': 'share/my_pkg/config/app.yaml',
    }

    assert task._get_data_files_mapping(desc, 'flit_core.buildapi') == {}
    assert task._get_data_files_mapping(desc, None) == {}


def test_build_task_script_override_and_record_update(tmp_path):
    """Test script_dir_override forwarding and unique RECORD updates."""
    task = PythonProjectBuildTask()

    pkg_path = tmp_path / 'src' / 'pkg'
    pkg_path.mkdir(parents=True)
    (pkg_path / 'pyproject.toml').write_text(
        '[project]\n'
        'name = "my-pkg"\n'
        'version = "0.1.0"\n'
        '[tool.hatch.build.targets.wheel.shared-data]\n'
        '"config/app.yaml" = "share/my_pkg/config/app.yaml"\n'
    )
    (pkg_path / 'config').mkdir()
    src_cfg = pkg_path / 'config' / 'app.yaml'
    src_cfg.write_text('key: val\n')

    desc = PackageDescriptor(str(pkg_path))
    desc.name = 'my-pkg'
    desc.type = 'python.project'

    build_base = tmp_path / 'build'
    install_base = tmp_path / 'install'
    build_base.mkdir()
    install_base.mkdir()

    # Pre-populate static copy and RECORD entry as install_wheel would
    dst_cfg = install_base / 'share' / 'my_pkg' / 'config' / 'app.yaml'
    dst_cfg.parent.mkdir(parents=True)
    dst_cfg.write_text('key: static\n')

    dist_info_dir = install_base / 'my_pkg-0.1.0.dist-info'
    dist_info_dir.mkdir(parents=True)
    (dist_info_dir / 'RECORD').write_text(
        'share/my_pkg/config/app.yaml,sha256=abc,11\n'
    )

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
    mock_hook_caller.backend_name = 'hatchling.build'
    mock_hook_caller.list_hooks = AsyncMock(return_value=['build_editable'])
    mock_whl = 'my_pkg-0.1.0-py3-none-any.whl'
    mock_hook_caller.call_hook = AsyncMock(return_value=mock_whl)

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
    ) as mock_install_wheel:
        result = run_until_complete(
            task.build(script_dir_override='lib/my_pkg')
        )
        assert result is None
        mock_install_wheel.assert_called_once_with(
            build_base / 'wheel' / mock_whl,
            str(install_base),
            script_dir_override='lib/my_pkg',
        )

    assert dst_cfg.is_symlink()
    record_entries = [
        line.split(',', 2)
        for line in (dist_info_dir / 'RECORD').read_text().splitlines()
        if ',' in line
    ]
    cfg_entries = [
        rec for rec in record_entries
        if rec[0] == 'share/my_pkg/config/app.yaml'
    ]
    assert cfg_entries == [['share/my_pkg/config/app.yaml', '', '']]
