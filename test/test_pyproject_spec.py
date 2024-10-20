# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.python_project.spec import load_and_cache_spec


def test_pyproject_missing(tmp_path):
    desc = PackageDescriptor(tmp_path)

    spec = load_and_cache_spec(desc)
    assert spec.get('build-system') == {
        'build-backend': 'setuptools.build_meta:__legacy__',
        'requires': ['setuptools >= 40.8.0', 'wheel'],
    }


def test_pyproject_empty(tmp_path):
    desc = PackageDescriptor(tmp_path)

    (tmp_path / 'pyproject.toml').write_text('')

    spec = load_and_cache_spec(desc)
    assert spec.get('build-system') == {
        'build-backend': 'setuptools.build_meta:__legacy__',
        'requires': ['setuptools >= 40.8.0', 'wheel'],
    }


def test_specified(tmp_path):
    desc = PackageDescriptor(tmp_path)

    (tmp_path / 'pyproject.toml').write_text('\n'.join((
        '[build-system]',
        'build-backend = "my_build_backend.meta"',
        'requires = ["my-build-backend"]',
    )))

    spec = load_and_cache_spec(desc)
    assert spec.get('build-system') == {
        'build-backend': 'my_build_backend.meta',
        'requires': ['my-build-backend'],
    }

    # truncate the pyproject.toml and call again
    # this verifies that the spec is cached
    (tmp_path / 'pyproject.toml').write_text('')

    spec = load_and_cache_spec(desc)
    assert spec.get('build-system') == {
        'build-backend': 'my_build_backend.meta',
        'requires': ['my-build-backend'],
    }
