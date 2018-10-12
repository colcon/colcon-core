# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.dependency_descriptor import DependencyDescriptor
from colcon_core.package_identification import logger
from colcon_core.package_identification \
    import PackageIdentificationExtensionPoint
from colcon_core.plugin_system import satisfies_version
from distlib.util import parse_requirement
from distlib.version import NormalizedVersion
try:
    from setuptools.config import read_configuration
except ImportError as e:
    from pkg_resources import get_distribution
    from pkg_resources import parse_version
    setuptools_version = get_distribution('setuptools').version
    minimum_version = '30.3.0'
    if parse_version(setuptools_version) < parse_version(minimum_version):
        e.msg += ', ' \
            "'setuptools' needs to be at least version {minimum_version}, if" \
            ' a newer version is not available from the package manager use ' \
            "'pip3 install -U setuptools' to update to the latest version" \
            .format_map(locals())
    raise


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
    :rtype: dict(string, set(DependencyDescriptor))
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
            dependencies[dependency_type].add(
                create_dependency_descriptor(dep))
    return dependencies


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
            logger.warn(
                "Ignoring unknown symbol '{symbol}' in '{requirement}'"
                .format(locals()))
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
