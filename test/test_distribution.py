# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import compileall
from pathlib import Path
import shutil
import subprocess
import sys

import colcon_core.python_project.distribution
from colcon_core.python_project.distribution import InstalledDistribution
import pytest


TEST_DISTS_ROOT = Path(__file__).parent / 'mock_distributions'
TEST_DISTS_PYTHONPATH = TEST_DISTS_ROOT / 'lib' / 'python' / 'site-packages'


def assert_path_patterns(candidates, patterns):
    candidates = set(candidates)
    for pattern in patterns:
        matches = {path for path in candidates if path.match(pattern)}
        assert matches, f"No matching path for pattern '{pattern}'"
        candidates.difference_update(matches)
    assert not candidates, 'Unexpected paths not matching any patterns'


def expected_bin_path(name):
    if sys.platform == 'win32':
        return 'Scripts/' + name + '.exe'
    return 'bin/' + name


@pytest.fixture
def dist_info_compiled(tmp_path):
    site_path = tmp_path / 'lib' / 'python' / 'site-packages'
    site_path.mkdir(parents=True)

    metadata_path = site_path / 'typical_dist_info-0.0.0.dist-info'

    shutil.copytree(
        TEST_DISTS_PYTHONPATH / 'typical_dist_info-0.0.0.dist-info',
        metadata_path)
    shutil.copytree(
        TEST_DISTS_PYTHONPATH / 'typical_dist_info',
        site_path / 'typical_dist_info')
    shutil.copyfile(
        TEST_DISTS_PYTHONPATH / 'typical_dist_info_again.py',
        site_path / 'typical_dist_info_again.py')
    compileall.compile_dir(site_path, quiet=1)

    yield metadata_path


@pytest.fixture
def dist_info_compiled_and_listed(dist_info_compiled):
    tmp_path = dist_info_compiled.parent
    compiled = set(tmp_path.rglob('__pycache__/*.pyc'))
    compiled_relative = sorted(pyc.relative_to(tmp_path) for pyc in compiled)
    with (dist_info_compiled / 'RECORD').open('a') as f:
        f.writelines(f'{pyc},,\n' for pyc in compiled_relative)
    yield dist_info_compiled


def test_discover():
    dists = list(InstalledDistribution.discover(path=[TEST_DISTS_PYTHONPATH]))
    assert all(isinstance(d, (InstalledDistribution,)) for d in dists)
    assert all(d.name for d in dists)
    assert {d.name for d in dists} == {
        'typical-dist-info',
        'typical-egg-info',
        'typical-egg-link',
    }


def test_dist_info():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_dist_info-0.0.0.dist-info'
    dist = InstalledDistribution.at(meta_path)
    assert dist.name
    assert_path_patterns(dist.get_installed_files(), (
        'typical_dist_info/__init__.py',
        'typical_dist_info/submodule/__init__.py',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
        'typical_dist_info_again.py',
    ))


def test_dist_info_compiled(dist_info_compiled):
    dist = InstalledDistribution.at(dist_info_compiled)
    assert dist.name
    assert_path_patterns(dist.get_installed_files(), (
        '__pycache__/typical_dist_info_again.*.pyc',
        'typical_dist_info/__init__.py',
        'typical_dist_info/__pycache__/__init__.*.pyc',
        'typical_dist_info/submodule/__init__.py',
        'typical_dist_info/submodule/__pycache__/__init__.*.pyc',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
        'typical_dist_info_again.py',
    ))


def test_dist_info_compiled_and_listed(dist_info_compiled_and_listed):
    dist = InstalledDistribution.at(dist_info_compiled_and_listed)
    assert dist.name
    assert_path_patterns(dist.get_installed_files(), (
        '__pycache__/typical_dist_info_again.*.pyc',
        'typical_dist_info/__init__.py',
        'typical_dist_info/__pycache__/__init__.*.pyc',
        'typical_dist_info/submodule/__init__.py',
        'typical_dist_info/submodule/__pycache__/__init__.*.pyc',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
        'typical_dist_info_again.py',
    ))


def test_egg_info():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_egg_info-0.0.0.egg-info'
    dist = InstalledDistribution.at(meta_path)
    assert dist.name
    assert_path_patterns(dist.get_installed_files(), (
        '../../../' + expected_bin_path('typical_egg_info'),
        'typical_egg_info/__init__.py',
        'typical_egg_info/submodule/__init__.py',
        'typical_egg_info-0.0.0.egg-info/PKG-INFO',
        'typical_egg_info-0.0.0.egg-info/entry_points.txt',
        'typical_egg_info-0.0.0.egg-info/top_level.txt',
        'typical_egg_info_again.py',
    ))


def test_egg_link():
    dists = InstalledDistribution.discover(path=[TEST_DISTS_PYTHONPATH])
    dist = next(dist for dist in dists if dist.name == 'typical-egg-link')
    assert dist.name
    assert_path_patterns(dist.get_installed_files(), (
        '../../../' + expected_bin_path('typical_egg_link'),
        'typical-egg-link.egg-link',
    ))


def test_debug_dump():
    """
    Smoke test for distribution.__main__.

    This function is really just used for debugging, so this test just
    exercises the code and doesn't actually validate the output.
    """
    meta_path = TEST_DISTS_PYTHONPATH
    cmd = [
        sys.executable,
        '-B',
        colcon_core.python_project.distribution.__file__,
    ]
    res = subprocess.run(cmd, cwd=meta_path, check=True, capture_output=True)
    assert res.stdout

    cmd.append(str(meta_path))
    res = subprocess.run(cmd, cwd=meta_path, check=True, capture_output=True)
    assert res.stdout
