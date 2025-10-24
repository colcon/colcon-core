# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import compileall
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import sys

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
    compileall.compile_dir(tmp_path / 'typical_dist_info', quiet=1)
    yield tmp_path / 'typical_dist_info-0.0.0.dist-info'


def test_dist_info():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_dist_info-0.0.0.dist-info'
    dist = AllFilesDistribution.at(meta_path)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical_dist_info/__init__.py',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
    )]


def test_dist_info_post_compiled(dist_info_compiled):
    dist = AllFilesDistribution.at(dist_info_compiled)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical_dist_info/__init__.py',
        'typical_dist_info/__pycache__/__init__.' + CACHE_TAG + '.pyc',
        'typical_dist_info-0.0.0.dist-info/METADATA',
        'typical_dist_info-0.0.0.dist-info/RECORD',
    )]


def test_egg_info():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical_egg_info-0.0.0.egg-info'
    dist = AllFilesDistribution.at(meta_path)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical_egg_info/__init__.py',
        'typical_egg_info-0.0.0.egg-info/PKG-INFO',
        'typical_egg_info-0.0.0.egg-info/top_level.txt',
    )]


def test_egg_link():
    meta_path = TEST_DISTS_PYTHONPATH / 'typical-egg-link.egg-link'
    dist = AllFilesDistribution.at(meta_path)
    assert sorted(dist.all_files) == [PurePosixPath(p) for p in (
        'typical-egg-link.egg-link',
    )]
