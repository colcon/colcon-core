# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Package identification for PEP 621 packages."""

from colcon_core.package_identification import logger
from colcon_core.package_identification \
    import PackageIdentificationExtensionPoint
from colcon_core.plugin_system import satisfies_version
from colcon_core.python_project.spec import load_and_cache_spec
from colcon_core.python_project.spec import SPEC_NAME


class PEP621PackageIdentification(PackageIdentificationExtensionPoint):
    """Identify Python packages with `pyproject.toml` metadata."""

    # the priority needs to be lower than the extensions identifying packages
    # using setup.py and/or setup.cfg files.
    PRIORITY = 90

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            PackageIdentificationExtensionPoint.EXTENSION_POINT_VERSION,
            '^1.0')

    def identify(self, desc):  # noqa: D102
        if desc.type is not None and desc.type != 'python.project':
            return

        spec_file = desc.path / SPEC_NAME
        if not spec_file.is_file():
            return

        spec = load_and_cache_spec(desc)
        name = spec.get('project', {}).get('name')
        if not name:
            return

        if desc.name is not None and desc.name != name:
            msg = 'Package name already set to different value'
            logger.error(msg)
            raise RuntimeError(msg)
        desc.name = name
        desc.type = 'python.project'
