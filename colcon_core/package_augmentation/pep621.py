# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Package augmentation for PEP 621 packages."""

import logging

from colcon_core.package_augmentation \
    import PackageAugmentationExtensionPoint
from colcon_core.package_augmentation.python \
    import create_dependency_descriptor
from colcon_core.plugin_system import satisfies_version
from colcon_core.python_project.spec import load_and_cache_spec
from colcon_core.python_project.spec import SPEC_NAME


class PEP621PackageAugmentation(PackageAugmentationExtensionPoint):
    """Augment Python packages with static metadata from `pyproject.toml`."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            PackageAugmentationExtensionPoint.EXTENSION_POINT_VERSION,
            '^1.0')

        # avoid debug message from asyncio when colcon uses debug log level
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.INFO)

    def augment_package(  # noqa: D102
        self, desc, *, additional_argument_names=None
    ):
        if desc.type != 'python.project':
            return

        spec_file = desc.path / SPEC_NAME
        if not spec_file.is_file():
            return

        spec = load_and_cache_spec(desc)
        desc.dependencies.setdefault('build', set())
        desc.dependencies['build'].update(
            create_dependency_descriptor(d)
            for d in spec['build-system'].get('requires') or ())

        project = spec.get('project', {})
        desc.dependencies.setdefault('run', set())
        desc.dependencies['run'].update(
            create_dependency_descriptor(d)
            for d in project.get('dependencies') or ())

        optional_deps = project.get('optional-dependencies', {})
        desc.dependencies.setdefault('test', set())
        desc.dependencies['test'].update(
            create_dependency_descriptor(d)
            for d in optional_deps.get('test') or ())

        version = project.get('version')
        if version:
            desc.metadata['version'] = version

        maintainers = project.get('maintainers')
        if not maintainers:
            maintainers = project.get('authors')
        if maintainers:
            desc.metadata.setdefault('maintainers', [])
            for entry in maintainers:
                email = entry.get('email')
                if not email:
                    continue
                name = entry.get('name')
                rfc822 = f'{name} <{email}>' if name else email
                if rfc822 not in desc.metadata['maintainers']:
                    desc.metadata['maintainers'].append(rfc822)
