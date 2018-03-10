# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import re

from colcon_core.package_identification import logger
from colcon_core.package_identification \
    import PackageIdentificationExtensionPoint
from colcon_core.plugin_system import satisfies_version
from setuptools.config import read_configuration


class PythonPackageIdentification(PackageIdentificationExtensionPoint):
    """Identify Python packages with `setup.cfg` files."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            PackageIdentificationExtensionPoint.EXTENSION_POINT_VERSION,
            '^1.0')

    def identify(self, desc):  # noqa: D102
        if desc.type is not None and desc.type != 'python':
            return

        setup_py = desc.path / 'setup.py'
        if not setup_py.is_file():
            return

        setup_cfg = desc.path / 'setup.cfg'
        if not setup_cfg.is_file():
            return

        config = get_configuration(setup_cfg)
        name = config.get('metadata', {}).get('name')
        if not name:
            return

        desc.type = 'python'
        if desc.name is not None and desc.name != name:
            msg = 'Package name already set to different value'
            logger.error(msg)
            raise RuntimeError(msg)
        desc.name = name

        options = config.get('options', {})
        dependencies = extract_dependencies(options)
        for k, v in dependencies.items():
            desc.dependencies[k] |= v

        def getter(env):
            nonlocal options
            return options

        desc.metadata['get_python_setup_options'] = getter


def get_configuration(setup_cfg):
    """
    Read the setup.cfg file.

    :param setup_cfg: The path of the setup.cfg file
    :returns: The configuration data
    :rtype: dict
    """
    return read_configuration(str(setup_cfg))


def extract_dependencies(options):
    """
    Get the dependencies of the package.

    :param options: The dictionary from the options section of the setup.cfg
      file
    :returns: The dependencies
    :rtype: dict
    """
    mapping = {
        'setup_requires': 'build',
        'install_requires': 'run',
        'tests_require': 'test',
    }
    dependencies = {}
    for option_name, dependency_type in mapping.items():
        dependencies[dependency_type] = set()
        for dep in options.get(option_name, []):
            # remove environmental markers (separated by semicolons)
            # and version specifiers (separated by comparison operators)
            name = re.split(r';|<|>|<=|>=|==|!=', dep)[0].rstrip()
            dependencies[dependency_type].add(name)
    return dependencies
