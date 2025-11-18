# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import compileall
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys

import colcon_core.python_project.distribution
from colcon_core.python_project.distribution import AllFilesDistribution
import pytest


CACHE_TAG = sys.implementation.cache_tag
TEST_DISTS_ROOT = Path(__file__).parent / 'mock_distributions'
TEST_DISTS_PYTHONPATH = TEST_DISTS_ROOT / 'lib' / 'python' / 'site-packages'


@pytest.fixture
def dist_info_compiled(tmp_path):
    shutil.copytree(
        TEST_DISTS_PYTHONPATH / 'typical_dist_info-0.0.0.dist-info',
        tmp_path / 'typical_dist_info-0.0.0.dist-info')
    shutil.copytree(
        TEST_DISTS_PYTHONPATH / 'typical_dist_info',
        tmp_path / 'typical_dist_info')
    shutil.copyfile(
        TEST_DISTS_PYTHONPATH / 'typical_dist_info_again.py',
        tmp_path / 'typical_dist_info_again.py')
    compileall.compile_dir(tmp_path, quiet=1)
    yield tmp_path / 'typical_dist_info-0.0.0.dist-info'


@pytest.fixture
def dist_info_compiled_and_listed(dist_info_compiled):
    tmp_path = dist_info_compiled.parent
    compiled = set(tmp_path.rglob('__pycache__/*.pyc'))
    compiled_relative = sorted(pyc.relative_to(tmp_path) for pyc in compiled)
    with (dist_info_compiled / 'RECORD').open('a') as f:
        f.writelines(f'{pyc},,\n' for pyc in compiled_relative)
    yield dist_info_compiled


def test_dist_info():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_dist_info-0.0.0.dist-info'
    dist = AllFilesDistribution.at(meta_path)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical_dist_info/__init__.py',
        'typical_dist_info/submodule/__init__.py',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
        'typical_dist_info_again.py',
    )]


def test_dist_info_compiled(dist_info_compiled):
    dist = AllFilesDistribution.at(dist_info_compiled)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        f'__pycache__/typical_dist_info_again.{CACHE_TAG}.pyc',
        'typical_dist_info/__init__.py',
        f'typical_dist_info/__pycache__/__init__.{CACHE_TAG}.pyc',
        'typical_dist_info/submodule/__init__.py',
        f'typical_dist_info/submodule/__pycache__/__init__.{CACHE_TAG}.pyc',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
        'typical_dist_info_again.py',
    )]


def test_dist_info_compiled_and_listed(dist_info_compiled_and_listed):
    dist = AllFilesDistribution.at(dist_info_compiled_and_listed)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        f'__pycache__/typical_dist_info_again.{CACHE_TAG}.pyc',
        'typical_dist_info/__init__.py',
        f'typical_dist_info/__pycache__/__init__.{CACHE_TAG}.pyc',
        'typical_dist_info/submodule/__init__.py',
        f'typical_dist_info/submodule/__pycache__/__init__.{CACHE_TAG}.pyc',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
        'typical_dist_info_again.py',
    )]


def test_egg_info():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_egg_info-0.0.0.egg-info'
    dist = AllFilesDistribution.at(meta_path)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical_egg_info/__init__.py',
        'typical_egg_info/submodule/__init__.py',
        'typical_egg_info-0.0.0.egg-info/PKG-INFO',
        'typical_egg_info-0.0.0.egg-info/top_level.txt',
        'typical_egg_info_again.py',
    )]


def test_egg_link():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical-egg-link.egg-link'
    dist = AllFilesDistribution.at(meta_path)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical-egg-link.egg-link',
    )]


def test_debug_dump():
    """
    Smoke test for distribution.__main__.

    This function is really just used for debugging, so this test just
    exercises the code and doesn't actually validate the output.
    """
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_dist_info-0.0.0.dist-info'
    cmd = [
        sys.executable,
        '-B',
        colcon_core.python_project.distribution.__file__,
    ]
    subprocess.run(cmd, cwd=meta_path, check=True)

    cmd.append(str(meta_path))
    subprocess.run(cmd, cwd=meta_path, check=True)
