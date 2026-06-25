# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Tests for package uninstallation utilities."""

from pathlib import Path
import shutil

from colcon_core.python_project.distribution import _get_install_path
from colcon_core.python_project.distribution import InstalledDistribution
from colcon_core.python_project.wheel import remove_distributions
import pytest

TEST_DISTS_ROOT = Path(__file__).parent / 'mock_distributions'


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Set up a temporary workspace.

    This copies mock distributions into the real python path.

    :param Path tmp_path: pytest fixture providing a temp directory
    :returns: Path to the temporary workspace root
    """
    real_purelib = Path(_get_install_path('purelib', tmp_path))
    real_purelib.mkdir(parents=True, exist_ok=True)

    # Copy site-packages contents into the real library path
    mock_site_packages = TEST_DISTS_ROOT / 'lib' / 'python' / 'site-packages'
    shutil.copytree(mock_site_packages, real_purelib, dirs_exist_ok=True)

    # Copy non-lib files (e.g. bin, Scripts, src) to workspace root
    for item in TEST_DISTS_ROOT.iterdir():
        if item.name == 'lib':
            continue
        dest = tmp_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy(item, dest)

    yield tmp_path


def test_remove_typical_dist_info(temp_workspace):
    """
    Test removal of a standard .dist-info package.

    :param Path temp_workspace: Temporary workspace fixture
    """
    name = 'typical-dist-info'
    libdir = Path(_get_install_path('purelib', temp_workspace))

    # Discover and verify distribution exists
    dists = list(
        InstalledDistribution.discover(
            name=name, path=[str(libdir)], prefix_path=temp_workspace
        )
    )
    dists = [
        d for d in dists
        if d.name.lower().replace('_', '-') == name.lower().replace('_', '-')
    ]
    assert len(dists) == 1
    dist = dists[0]

    # Keep track of expected file paths
    files = dist.get_installed_files()
    assert len(files) > 0
    file_paths = [dist.path.parent / f for f in files]
    for p in file_paths:
        assert p.exists()

    # Call uninstallation utility
    remove_distributions(name, temp_workspace)

    # Assert all files are deleted
    for p in file_paths:
        assert not p.exists()

    # Assert empty parent directories are cleaned up
    assert not (libdir / 'typical_dist_info').exists()
    assert not (libdir / 'typical_dist_info-0.0.0.dist-info').exists()


def test_remove_typical_egg_info(temp_workspace):
    """
    Test removal of a legacy .egg-info package.

    :param Path temp_workspace: Temporary workspace fixture
    """
    name = 'typical-egg-info'
    libdir = Path(_get_install_path('purelib', temp_workspace))

    # Discover and verify distribution exists
    dists = list(
        InstalledDistribution.discover(
            name=name, path=[str(libdir)], prefix_path=temp_workspace
        )
    )
    dists = [
        d for d in dists
        if d.name.lower().replace('_', '-') == name.lower().replace('_', '-')
    ]
    assert len(dists) == 1
    dist = dists[0]

    # Keep track of expected file paths
    files = dist.get_installed_files()
    assert len(files) > 0
    file_paths = [dist.path.parent / f for f in files]
    for p in file_paths:
        assert p.exists()

    # Call uninstallation utility
    remove_distributions(name, temp_workspace)

    # Assert all files are deleted
    for p in file_paths:
        assert not p.exists()

    # Assert empty parent directories are cleaned up
    assert not (libdir / 'typical_egg_info').exists()
    assert not (libdir / 'typical_egg_info-0.0.0.egg-info').exists()


def test_remove_typical_egg_link(temp_workspace):
    """
    Test removal of a legacy develop egg-link.

    :param Path temp_workspace: Temporary workspace fixture
    """
    name = 'typical-egg-link'
    libdir = Path(_get_install_path('purelib', temp_workspace))
    egg_link = libdir / 'typical-egg-link.egg-link'

    # Verify egg link exists initially
    assert egg_link.is_file()

    # Discover and verify distribution exists
    dists = list(
        InstalledDistribution.discover(
            name=name, path=[str(libdir)], prefix_path=temp_workspace
        )
    )
    dists = [
        d for d in dists
        if d.name.lower().replace('_', '-') == name.lower().replace('_', '-')
    ]
    assert len(dists) == 1
    dist = dists[0]

    # Keep track of expected file paths
    files = dist.get_installed_files()
    assert len(files) > 0
    file_paths = [dist.path.parent / f for f in files]
    for p in file_paths:
        assert p.exists()

    # Call uninstallation utility
    remove_distributions(name, temp_workspace)

    # Assert all files are deleted
    for p in file_paths:
        assert not p.exists()

    # Assert egg-link file is deleted
    assert not egg_link.exists()


def test_remove_nonexistent_distribution(temp_workspace):
    """
    Test uninstallation of a package that does not exist on disk.

    :param Path temp_workspace: Temporary workspace fixture
    """
    name = 'nonexistent-package'
    # Should complete without error
    remove_distributions(name, temp_workspace)
