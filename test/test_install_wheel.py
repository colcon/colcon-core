# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Tests for package installation utilities."""

from base64 import urlsafe_b64encode
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from colcon_core.python_project.distribution import _get_install_path
from colcon_core.python_project.wheel import install_wheel


def create_dummy_wheel(
    wheel_path, name, version, purelib=True, extra_files=None,
    console_scripts=None
):
    """
    Create a minimal dummy wheel file.

    :param Path wheel_path: Target path to save the wheel file
    :param str name: Distribution name
    :param str version: Distribution version
    :param bool purelib: True for purelib, False for platlib
    :param dict extra_files: Mapping of path in zip to file content
    :param dict console_scripts: Mapping of script names to entry points
    """
    dist_info = f'{name}-{version}.dist-info'

    files = {}

    # WHEEL file
    wheel_content = (
        'Wheel-Version: 1.0\n'
        'Generator: test\n'
        f"Root-Is-Purelib: {'true' if purelib else 'false'}\n"
        'Tag: py3-none-any\n'
    )
    files[f'{dist_info}/WHEEL'] = wheel_content

    # METADATA file
    metadata_content = (
        'Metadata-Version: 2.1\n'
        f'Name: {name}\n'
        f'Version: {version}\n'
    )
    files[f'{dist_info}/METADATA'] = metadata_content

    # entry_points.txt
    if console_scripts:
        ep_content = '[console_scripts]\n'
        for script_name, target in console_scripts.items():
            ep_content += f'{script_name} = {target}\n'
        files[f'{dist_info}/entry_points.txt'] = ep_content

    # Extra files
    if extra_files:
        for path, content in extra_files.items():
            files[path] = content

    # Compute RECORD
    record_lines = []
    with ZipFile(wheel_path, 'w', compression=ZIP_DEFLATED) as zf:
        for path, content in files.items():
            content_bytes = (
                content.encode('utf-8')
                if isinstance(content, str) else content
            )
            zf.writestr(path, content_bytes)

            digest = urlsafe_b64encode(
                hashlib.sha256(content_bytes).digest()
            ).rstrip(b'=').decode('utf-8')
            size = len(content_bytes)
            record_lines.append(f'{path},sha256={digest},{size}')

        # RECORD itself is listed with empty hash and size
        record_lines.append(f'{dist_info}/RECORD,,')
        zf.writestr(
            f'{dist_info}/RECORD',
            '\n'.join(record_lines) + '\n'
        )


def test_install_wheel_purelib(tmp_path):
    """
    Test installation of a pure Python wheel.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    wheel_path = tmp_path / 'dummy_pkg-1.0.0-py3-none-any.whl'
    extra_files = {
        'dummy_pkg/__init__.py': '# init\n',
        'dummy_pkg/module.py': 'def foo(): pass\n',
    }
    create_dummy_wheel(
        wheel_path, 'dummy_pkg', '1.0.0', extra_files=extra_files)

    install_base = tmp_path / 'install'
    dist_info = install_wheel(wheel_path, install_base)

    libdir = Path(_get_install_path('purelib', install_base))

    # Verify files were extracted to purelib
    assert dist_info.is_dir()
    assert dist_info.name == 'dummy_pkg-1.0.0.dist-info'
    assert (libdir / 'dummy_pkg' / '__init__.py').is_file()
    assert (libdir / 'dummy_pkg' / 'module.py').is_file()

    # Verify INSTALLER metadata exists
    installer_file = dist_info / 'INSTALLER'
    assert installer_file.is_file()
    assert installer_file.read_text(encoding='utf-8').strip() == 'colcon-core'

    # Verify RECORD exists
    record_file = dist_info / 'RECORD'
    assert record_file.is_file()


def test_install_wheel_platlib(tmp_path):
    """
    Test installation of a platform-specific wheel.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    wheel_path = tmp_path / 'dummy_pkg-1.0.0-py3-none-any.whl'
    extra_files = {
        'dummy_pkg/__init__.py': '# init\n',
    }
    create_dummy_wheel(
        wheel_path, 'dummy_pkg', '1.0.0', purelib=False,
        extra_files=extra_files
    )

    install_base = tmp_path / 'install'
    dist_info = install_wheel(wheel_path, install_base)

    libdir = Path(_get_install_path('platlib', install_base))

    assert dist_info.is_dir()
    assert (libdir / 'dummy_pkg' / '__init__.py').is_file()


def test_install_wheel_with_console_scripts(tmp_path):
    """
    Test installation of a wheel with entry point console scripts.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    wheel_path = tmp_path / 'dummy_pkg-1.0.0-py3-none-any.whl'
    console_scripts = {
        'dummy-cli': 'dummy_pkg.main:cli_entry',
    }
    create_dummy_wheel(
        wheel_path, 'dummy_pkg', '1.0.0', console_scripts=console_scripts
    )

    install_base = tmp_path / 'install'
    install_wheel(wheel_path, install_base)

    script_dir = Path(_get_install_path('scripts', install_base))
    scripts = list(script_dir.glob('dummy-cli*'))
    assert len(scripts) > 0


def test_install_wheel_with_data_files(tmp_path):
    """
    Test installation of a wheel with package data files.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    wheel_path = tmp_path / 'dummy_pkg-1.0.0-py3-none-any.whl'
    extra_files = {
        'dummy_pkg-1.0.0.data/data/share/dummy_pkg/resource.txt':
        'resource data\n',
    }
    create_dummy_wheel(
        wheel_path, 'dummy_pkg', '1.0.0', extra_files=extra_files
    )

    install_base = tmp_path / 'install'
    install_wheel(wheel_path, install_base)

    # Path gets resolved under install_base/share/dummy_pkg/resource.txt
    data_file = install_base / 'share' / 'dummy_pkg' / 'resource.txt'
    assert data_file.is_file()
    assert data_file.read_text(encoding='utf-8') == 'resource data\n'


def test_install_wheel_cleanup_old(tmp_path):
    """
    Test that installing a package cleans up the older version.

    :param Path tmp_path: pytest fixture providing a temp directory
    """
    install_base = tmp_path / 'install'
    libdir = Path(_get_install_path('purelib', install_base))

    # Install version 1.0.0
    wheel_v1 = tmp_path / 'dummy_pkg-1.0.0-py3-none-any.whl'
    create_dummy_wheel(
        wheel_v1, 'dummy_pkg', '1.0.0',
        extra_files={'dummy_pkg/v1.py': '# v1\n'}
    )
    dist_info_v1 = install_wheel(wheel_v1, install_base)
    assert dist_info_v1.is_dir()
    assert (libdir / 'dummy_pkg' / 'v1.py').is_file()

    # Install version 2.0.0
    wheel_v2 = tmp_path / 'dummy_pkg-2.0.0-py3-none-any.whl'
    create_dummy_wheel(
        wheel_v2, 'dummy_pkg', '2.0.0',
        extra_files={'dummy_pkg/v2.py': '# v2\n'}
    )
    dist_info_v2 = install_wheel(wheel_v2, install_base)

    # Verify v1 files are deleted
    assert not dist_info_v1.exists()
    assert not (libdir / 'dummy_pkg' / 'v1.py').exists()

    # Verify v2 files are installed
    assert dist_info_v2.is_dir()
    assert (libdir / 'dummy_pkg' / 'v2.py').is_file()
