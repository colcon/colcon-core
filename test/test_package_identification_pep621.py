# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Tests for PEP621PackageIdentification."""

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_identification.pep621 \
    import PEP621PackageIdentification
from colcon_core.package_identification.python \
    import PythonPackageIdentification
import pytest


def test_priority():
    """Test priority of PEP621 Package Identification vs python."""
    ext = PEP621PackageIdentification()
    python_ext = PythonPackageIdentification()
    assert ext.PRIORITY < python_ext.PRIORITY


def test_identify(tmp_path):
    """Test PEP621PackageIdentification identify method."""
    ext = PEP621PackageIdentification()

    # Ignored if desc.type is already set to something else
    desc = PackageDescriptor(str(tmp_path))
    desc.type = 'other'
    assert ext.identify(desc) is None
    assert desc.name is None

    # Ignored if pyproject.toml does not exist
    desc = PackageDescriptor(str(tmp_path))
    assert ext.identify(desc) is None
    assert desc.name is None

    # Ignored if pyproject.toml exists but has no project.name
    (tmp_path / 'pyproject.toml').write_text(
        '[build-system]\n'
        'requires = ["setuptools"]\n'
    )
    desc = PackageDescriptor(str(tmp_path))
    assert ext.identify(desc) is None
    assert desc.name is None

    # PEP 621 identification via pyproject.toml
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\n'
        'name = "pep621-pkg"\n'
    )
    desc = PackageDescriptor(str(tmp_path))
    assert ext.identify(desc) is None
    assert desc.name == 'pep621-pkg'
    assert desc.type == 'python.project'

    # Mismatched existing name raises RuntimeError
    desc = PackageDescriptor(str(tmp_path))
    desc.name = 'mismatched-name'
    with pytest.raises(RuntimeError) as e:
        ext.identify(desc)
    assert 'Package name already set to different value' in str(e.value)
