# Copyright 2016-2019 Dirk Thomas
# Copyright 2019 Rover Robotics via Dan Rose
# Licensed under the Apache License, Version 2.0

import multiprocessing
import os
from traceback import format_exc
from typing import Optional
import warnings

from colcon_core.dependency_descriptor import DependencyDescriptor
from colcon_core.package_identification import logger
from colcon_core.package_identification \
    import PackageIdentificationExtensionPoint
from colcon_core.plugin_system import satisfies_version
from colcon_core.run_setup_py import run_setup_py
from distlib.util import parse_requirement
from distlib.version import NormalizedVersion

_process_pool = multiprocessing.Pool()


class PythonPackageIdentification(PackageIdentificationExtensionPoint):
    """Identify Python packages with `setup.py` and opt. `setup.cfg` files."""

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

        # after this point, we are convinced this is a Python package,
        # so we should fail with an Exception instead of silently

        config = get_setup_result(setup_py, env=None)

        name = config['metadata'].name
        if not name:
            raise RuntimeError(
                "The Python package in '{setup_py.parent}' has an invalid "
                'package name'.format_map(locals()))

        desc.type = 'python'
        if desc.name is not None and desc.name != name:
            raise RuntimeError(
                "The Python package in '{setup_py.parent}' has the name "
                "'{name}' which is different from the already set package "
                "name '{desc.name}'".format_map(locals()))
        desc.name = name

        desc.metadata['version'] = config['metadata'].version

        for dependency_type, option_name in [
            ('build', 'setup_requires'),
            ('run', 'install_requires'),
            ('test', 'tests_require')
        ]:
            desc.dependencies[dependency_type] = {
                create_dependency_descriptor(d)
                for d in config[option_name] or ()}

        def getter(env):
            nonlocal setup_py
            return get_setup_result(setup_py, env=env)

        desc.metadata['get_python_setup_options'] = getter


def get_configuration(setup_cfg):
    """
    Return the configuration values defined in the setup.cfg file.

    The function exists for backward compatibility with older versions of
    colcon-ros.

    :param setup_cfg: The path of the setup.cfg file
    :returns: The configuration data
    :rtype: dict
    """
    warnings.warn(
        'colcon_core.package_identification.python.get_configuration() will '
        'be removed in the future', DeprecationWarning, stacklevel=2)
    config = get_setup_result(setup_cfg.parent / 'setup.py', env=None)
    return {
        'metadata': {'name': config['metadata'].name},
        'options': config
    }


def get_setup_result(setup_py, *, env: Optional[dict]):
    """
    Spin up a subprocess to run setup.py, with the given environment.

    :param setup_py: Path to a setup.py script
    :param env: Environment variables to set before running setup.py
    :return: Dictionary of data describing the package.
    :raise: RuntimeError if the setup script encountered an error
    """
    env_copy = os.environ.copy()
    if env is not None:
        env_copy.update(env)

    try:
        return _process_pool.apply(
            run_setup_py,
            kwds={
                'cwd': os.path.abspath(str(setup_py.parent)),
                'env': env_copy,
                'script_args': ('--dry-run',),
                'stop_after': 'config'
            }
        )
    except Exception as e:
        raise RuntimeError(
            'Failure when trying to run setup script {}: {}'
            .format(setup_py, format_exc())) from e


def create_dependency_descriptor(requirement_string):
    """
    Create a DependencyDescriptor from a PEP440 compliant string.

    See https://www.python.org/dev/peps/pep-0440/#version-specifiers

    :param str requirement_string: a PEP440 compliant requirement string
    :return: A descriptor with version constraints from the requirement string
    :rtype: DependencyDescriptor
    """
    symbol_mapping = {
        '==': 'version_eq',
        '!=': 'version_neq',
        '<=': 'version_lte',
        '>=': 'version_gte',
        '>': 'version_gt',
        '<': 'version_lt',
    }

    requirement = parse_requirement(requirement_string)
    metadata = {}
    for symbol, version in (requirement.constraints or []):
        if symbol in symbol_mapping:
            metadata[symbol_mapping[symbol]] = version
        elif symbol == '~=':
            metadata['version_gte'] = version
            metadata['version_lt'] = _next_incompatible_version(version)
        else:
            logger.warning(
                "Ignoring unknown symbol '{symbol}' in '{requirement}'"
                .format_map(locals()))
    return DependencyDescriptor(requirement.name, metadata=metadata)


def _next_incompatible_version(version):
    """
    Find the next non-compatible version.

    This is for use with the ~= compatible syntax. It will provide
    the first version that this version must be less than in order
    to be compatible.

    :param str version: PEP 440 compliant version number
    :return: The first version after this version that is not compatible
    :rtype: str
    """
    normalized = NormalizedVersion(version)
    parse_tuple = normalized.parse(version)
    version_tuple = parse_tuple[1]

    *unchanged, increment, dropped = version_tuple
    incremented = increment + 1

    version = unchanged
    version.append(incremented)
    # versions have a minimum length of 2
    if len(version) == 1:
        version.append(0)
    return '.'.join(map(str, version))
