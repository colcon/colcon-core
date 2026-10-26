# Copyright 2019 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path

from colcon_core.environment_variable import EnvironDict
from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell import _get_pkg_name
from colcon_core.shell import check_dependency_availability
from colcon_core.shell import get_shell_extensions
from colcon_core.shell import logger
from colcon_core.shell import ShellExtensionPoint
from colcon_core.shell.template import expand_template

DSV_TYPE_APPEND_NON_DUPLICATE = 'append-non-duplicate'
DSV_TYPE_PREPEND_NON_DUPLICATE = 'prepend-non-duplicate'
DSV_TYPE_PREPEND_NON_DUPLICATE_IF_EXISTS = 'prepend-non-duplicate-if-exists'
DSV_TYPE_SET = 'set'
DSV_TYPE_SET_IF_UNSET = 'set-if-unset'
DSV_TYPE_SOURCE = 'source'


class DsvShell(ShellExtensionPoint):
    """Generate `.dsv` files and derive the command environment from them."""

    # the priority needs to be higher than the default for primary shells
    # it is also higher than the priority of any shell which computes the
    # command environment by invoking a subprocess, since the descriptors
    # provide the same information without spawning one
    PRIORITY = 400

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(ShellExtensionPoint.EXTENSION_POINT_VERSION, '^2.2')

    def create_prefix_script(self, prefix_path, merge_install):  # noqa: D102
        return []

    def create_package_script(  # noqa: D102
        self, prefix_path, pkg_name, hooks
    ):
        pkg_env_path = prefix_path / 'share' / pkg_name / 'package.dsv'
        logger.info("Creating package descriptor '%s'" % pkg_env_path)
        expand_template(
            Path(__file__).parent / 'template' / 'package.dsv.em',
            pkg_env_path,
            {
                'hooks': hooks,
            })
        return [pkg_env_path]

    def create_hook_set_value(  # noqa: D102
        self, env_hook_name, prefix_path, pkg_name, name, value,
    ):
        hook_path = prefix_path / 'share' / pkg_name / 'hook' / \
            ('%s.dsv' % env_hook_name)
        logger.info("Creating environment descriptor '%s'" % hook_path)
        expand_template(
            Path(__file__).parent / 'template' / 'hook_set_value.dsv.em',
            hook_path,
            {
                'name': name,
                'value': value,
            })
        return hook_path

    def create_hook_append_value(  # noqa: D102
        self, env_hook_name, prefix_path, pkg_name, name, subdirectory,
    ):
        hook_path = prefix_path / 'share' / pkg_name / 'hook' / \
            ('%s.dsv' % env_hook_name)
        logger.info("Creating environment descriptor '%s'" % hook_path)
        expand_template(
            Path(__file__).parent / 'template' / 'hook_append_value.dsv.em',
            hook_path,
            {
                'type_': 'append-non-duplicate',
                'name': name,
                'value': subdirectory,
            })
        return hook_path

    def create_hook_prepend_value(  # noqa: D102
        self, env_hook_name, prefix_path, pkg_name, name, subdirectory,
    ):
        hook_path = prefix_path / 'share' / pkg_name / 'hook' / \
            ('%s.dsv' % env_hook_name)
        logger.info("Creating environment descriptor '%s'" % hook_path)
        expand_template(
            Path(__file__).parent / 'template' / 'hook_prepend_value.dsv.em',
            hook_path,
            {
                'type_': 'prepend-non-duplicate',
                'name': name,
                'value': subdirectory,
            })
        return hook_path

    async def generate_command_environment(  # noqa: D102
        self, task_name, build_base, dependencies,
    ):
        try:
            # check if all dependencies are available
            # removes dependencies available in the environment from the
            # parameter
            check_dependency_availability(
                dependencies, script_filename='package.dsv')
        except RuntimeError as e:  # noqa: F841
            # a prefix without descriptors can still be sourced by a shell,
            # which also reports the packages which need to be built
            raise SkipExtensionException(
                'Not all dependencies provide a descriptor')

        env = EnvironDict(os.environ)
        try:
            for dep, pkg_install_base in dependencies.items():
                prefix = str(pkg_install_base)
                _evaluate_dsv_file(
                    env,
                    os.path.join(
                        prefix, 'share', _get_pkg_name(dep), 'package.dsv'),
                    prefix)
        except _MissingDescriptorError as e:  # noqa: F841
            raise SkipExtensionException(
                f'Unable to determine the environment from descriptors: {e}')

        # the package scripts unset this variable after being sourced
        env.pop('COLCON_CURRENT_PREFIX', None)

        # write environment variables to file for debugging
        # the other shells create the directory with their command prefix
        # script, which this extension doesn't generate
        env_path = build_base / (
            'colcon_command_prefix_%s.dsv.env' % task_name)
        env_path.parent.mkdir(parents=True, exist_ok=True)
        with env_path.open('w') as h:
            for key in sorted(env.keys()):
                value = env[key]
                h.write(f'{key}={value}\n')

        return env


class _MissingDescriptorError(Exception):
    """A script which needs to be sourced has no descriptor to evaluate."""


_script_extensions = None


def _get_script_extensions():
    """Get the file extensions which a primary shell is able to source."""
    global _script_extensions
    if _script_extensions is None:
        _script_extensions = set()
        extensions = get_shell_extensions()
        for priority in extensions.keys():
            # only consider primary shell extensions
            if priority <= ShellExtensionPoint.PRIORITY:
                break
            for extension in extensions[priority].values():
                _script_extensions.update(extension.get_file_extensions())
    return _script_extensions


def _parse_dsv_file(dsv_path):
    """Parse a descriptor into a list of type and remainder tuples."""
    entries = []
    try:
        with open(dsv_path, 'r') as h:
            lines = h.read().splitlines()
    except OSError as e:  # noqa: F841
        raise _MissingDescriptorError(
            f"could not read '{dsv_path}': {e}") from e
    for i, line in enumerate(lines):
        # skip over empty or whitespace-only lines as well as comments
        if not line.strip() or line.startswith('#'):
            continue
        try:
            type_, remainder = line.split(';', 1)
        except ValueError:
            raise RuntimeError(
                "Line %d in '%s' doesn't contain a semicolon separating the "
                'type from the arguments' % (i + 1, dsv_path))
        entries.append((type_, remainder))

    return entries


def _flatten_dsv_file(dsv_path, prefix):
    """
    Resolve a descriptor and the descriptors it sources into a list of changes.

    This mirrors the `process_dsv_file` function of the `prefix_util.py`
    template, but instead of generating shell commands it collects the
    environment changes in the order in which they need to be applied.

    :param str dsv_path: The path of the descriptor
    :param str prefix: The path of the install prefix
    :returns: The type and remainder tuples to be applied in order
    :rtype: list
    :raises _MissingDescriptorError: if a script needs to be sourced for which
      no descriptor exists
    """
    changes = []
    basename_map = {}
    for type_, remainder in _parse_dsv_file(dsv_path):
        if type_ != DSV_TYPE_SOURCE:
            # handle non-source lines
            changes.append((type_, remainder))
            continue
        # group remaining source lines by basename
        path_without_ext, ext = os.path.splitext(remainder)
        extensions = basename_map.setdefault(path_without_ext, set())
        # the descriptor of a basename is considered either way, only script
        # extensions which a shell would source are relevant here
        if ext[1:] in _get_script_extensions():
            extensions.add(ext[1:])

    for basename, extensions in basename_map.items():
        if not os.path.isabs(basename):
            basename = os.path.join(prefix, basename)
        if os.path.exists(basename + '.dsv'):
            # process descriptors recursively
            changes += _flatten_dsv_file(basename + '.dsv', prefix)
        elif extensions:
            # a script without a descriptor can only be sourced by a shell
            raise _MissingDescriptorError(
                "no descriptor for '%s.%s'"
                % (basename, sorted(extensions)[0]))

    return changes


def _evaluate_dsv_file(env, dsv_path, prefix):
    """Apply a descriptor and the descriptors it sources to an environment."""
    for type_, remainder in _flatten_dsv_file(dsv_path, prefix):
        try:
            _apply_change(env, type_, remainder, prefix)
        except RuntimeError as e:
            raise RuntimeError("In '%s' %s" % (dsv_path, e)) from e


def _join_with_prefix(prefix, value):
    # the hook scripts are generated with native separators, so a descriptor
    # using the alternative separator must not result in a different value
    joined = os.path.join(prefix, value)
    if os.altsep:
        joined = joined.replace(os.altsep, os.sep)
    return joined


def _apply_change(env, type_, remainder, prefix):
    if type_ in (DSV_TYPE_SET, DSV_TYPE_SET_IF_UNSET):
        try:
            env_name, value = remainder.split(';', 1)
        except ValueError:
            raise RuntimeError(
                "doesn't contain a semicolon separating the environment name "
                'from the value')
        try_prefixed_value = \
            _join_with_prefix(prefix, value) if value else prefix
        if os.path.exists(try_prefixed_value):
            value = try_prefixed_value
        if type_ == DSV_TYPE_SET or not env.get(env_name):
            env[env_name] = value
    elif type_ in (
        DSV_TYPE_APPEND_NON_DUPLICATE,
        DSV_TYPE_PREPEND_NON_DUPLICATE,
        DSV_TYPE_PREPEND_NON_DUPLICATE_IF_EXISTS
    ):
        env_name_and_values = remainder.split(';')
        env_name = env_name_and_values[0]
        for value in env_name_and_values[1:]:
            if not value:
                value = prefix
            elif not os.path.isabs(value):
                value = _join_with_prefix(prefix, value)
            if (
                type_ == DSV_TYPE_PREPEND_NON_DUPLICATE_IF_EXISTS and
                not os.path.exists(value)
            ):
                continue
            # duplicates are being skipped and empty values dropped, the same
            # way the `prefix_util.py` template evaluates the descriptors
            values = [v for v in env.get(env_name, '').split(os.pathsep) if v]
            if value not in values:
                if type_ == DSV_TYPE_APPEND_NON_DUPLICATE:
                    values.append(value)
                else:
                    values.insert(0, value)
            env[env_name] = os.pathsep.join(values)
    else:
        raise RuntimeError(
            'contains an unknown environment hook type: ' + type_)
