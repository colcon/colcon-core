# Copyright 2016-2019 Dirk Thomas
# Copyright 2019 Rover Robotics
# Licensed under the Apache License, Version 2.0

import distutils.core
import multiprocessing
import os
from typing import Optional
import warnings

from colcon_core.dependency_descriptor import DependencyDescriptor
from colcon_core.package_identification import logger
from colcon_core.package_identification \
    import PackageIdentificationExtensionPoint
from colcon_core.plugin_system import satisfies_version
from distlib.util import parse_requirement
from distlib.version import NormalizedVersion


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

        if os.path.realpath(__file__).startswith(
            os.path.realpath(str(desc.path))
        ):
            # Bootstrapping colcon.
            # todo: is this really necessary?
            get_setup_fn = get_setup_result_in_process
        else:
            get_setup_fn = get_setup_result

        config = get_setup_fn(setup_py, env=None)

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
            nonlocal setup_py, get_setup_fn
            return get_setup_fn(setup_py, env=env)

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

    conn_recv, conn_send = multiprocessing.Pipe(duplex=False)
    with conn_send:
        p = multiprocessing.Process(
            target=_get_setup_result_target,
            args=(os.path.abspath(str(setup_py)), env_copy, conn_send),
        )
        p.start()
        p.join()
    with conn_recv:
        result_or_exception_string = conn_recv.recv()

    if isinstance(result_or_exception_string, dict):
        return result_or_exception_string
    raise RuntimeError(
        'Failure when trying to run setup script {}:\n{}'
        .format(setup_py, result_or_exception_string))


def _get_setup_result_target(setup_py: str, env: dict, conn_send):
    """
    Run setup.py in a modified environment.

    Helper function for get_setup_metadata. The resulting dict or error
    will be sent via conn_send instead of returned or thrown.

    :param setup_py: Absolute path to a setup.py script
    :param env: Environment variables to set before running setup.py
    :param conn_send: Connection to send the result as either a dict or an
        error string
    """
    import traceback
    try:
        # need to be in setup.py's parent dir to detect any setup.cfg
        os.chdir(os.path.dirname(setup_py))

        os.environ.clear()
        os.environ.update(env)

        result = distutils.core.run_setup(
            str(setup_py), ('--dry-run',), stop_after='config')

        conn_send.send(_distribution_to_dict(result))
    except BaseException:
        conn_send.send(traceback.format_exc())


def get_setup_result_in_process(setup_py, *, env: Optional[dict]):
    """
    Run setup.py in this process.

    Prefer get_setup_result, since it provides process isolation is
    threadsafe, and returns predictable errors.
    :param setup_py: Path to a setup.py script
    :param env: Environment variables to set before running setup.py
    :return: Dictionary of data describing the package.
    :raise: RuntimeError if the script doesn't appear to be a setup script.
            Any exception raised in the setup.py script.
    """
    save_env = os.environ.copy()
    save_cwd = os.getcwd()

    try:
        if env is not None:
            os.environ.update(env)
        os.chdir(str(setup_py.parent))
        dist = distutils.core.run_setup(
            'setup.py', ('--dry-run',), stop_after='config')
    finally:
        if env is not None:
            os.environ.clear()
            os.environ.update(save_env)
        os.chdir(save_cwd)
    return _distribution_to_dict(dist)


def _distribution_to_dict(distribution_object) -> dict:
    """Turn a distribution into a dict, discarding unpicklable attributes."""
    return {
        attr: value for attr, value in distribution_object.__dict__.items()
        if (
            # These *seem* useful but always have the value 0.
            # Look for their values in the 'metadata' object instead.
            attr not in distribution_object.display_option_names
            # Getter methods
            and not callable(value)
            # Private properties
            and not attr.startswith('_')
            # Objects that are generally not picklable
            and attr not in ('cmdclass', 'distclass', 'ext_modules')
        )}


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
