# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from concurrent.futures import CancelledError
import os
from pathlib import Path
import traceback

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_grouped_by_priority
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.subprocess import check_output

logger = colcon_logger.getChild(__name__)

"""Environment variable to enable all shell extensions."""
ALL_SHELLS_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_ALL_SHELLS', 'Flag to enable all shell extensions')

use_all_shell_extensions = os.environ.get(
    ALL_SHELLS_ENVIRONMENT_VARIABLE.name, False)


class ShellExtensionPoint:
    """
    The interface for shell extensions.

    An shell extension generates the scripts for a specific shell to setup the
    environment.

    For each instance the attribute `SHELL_NAME` is being set to the basename
    of the entry point registering the extension.
    """

    """The version of the shell extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """
    The default priority of shell extensions.

    A shell extension must use a higher priority than the default if and only
    if it is a "primary" shell.
    A "primary" shell does not depend on another shell to setup the
    environment, e.g. `sh`.
    An example for a "non-primary" shell would be `bash` which relies on the
    `sh` shell extension to setup environment variables and only contributes
    additional information like completion.

    All "non-primiry" shell extensions must use a priority equal to or lower
    than the default.
    """
    PRIORITY = 100

    def create_prefix_script(self, prefix_path, pkg_names, merge_install):
        """
        Create a script in the install prefix path.

        The script should call each package specific script in order.

        This method must be overridden in a subclass.

        :param Path prefix_path: The path of the install prefix
        :param list pkg_names: The package names
        :param bool merge_install: The flag if all packages share the same
          install prefix
        """
        raise NotImplementedError()

    def create_package_script(self, prefix_path, pkg_name, hooks):
        """
        Create a script for a specific package.

        The script should call each hook script in order.

        This method must be overridden in a subclass.

        :param Path prefix_path: The package specific install prefix
        :param str pkg_name: The package name
        :param list hooks: The relative paths to the hook scripts
        """
        raise NotImplementedError()

    def create_hook_set_value(
        self, env_hook_name, prefix_path, pkg_name, name, value,
    ):
        """
        Create a hook script to set an environment variable value.

        This method must be overridden in a subclass.

        :param str env_hook_name: The name of the hook script
        :param Path prefix_path: The path of the install prefix
        :param str pkg_name: The package name
        :param str name: The name of the environment variable
        :param str value: The value to be set
        :returns: The relative path to the created hook script
        :rtype: Path
        """
        raise NotImplementedError()

    def create_hook_append_value(
        self, env_hook_name, prefix_path, pkg_name, name, value,
    ):
        """
        Create a hook script to append a value to an environment variable.

        This method must be overridden in a subclass.

        :param str env_hook_name: The name of the hook script
        :param Path prefix_path: The path of the install prefix
        :param str pkg_name: The package name
        :param str name: The name of the environment variable
        :param str value: The value to be appended
        :returns: The relative path to the created hook script
        :rtype: Path
        """
        raise NotImplementedError()

    def create_hook_prepend_value(
        self, env_hook_name, prefix_path, pkg_name, name, subdirectory,
    ):
        """
        Create a hook script to prepend a value to an environment variable.

        This method must be overridden in a subclass.

        :param str env_hook_name: The name of the hook script
        :param Path prefix_path: The path of the install prefix
        :param str pkg_name: The package name
        :param str name: The name of the environment variable
        :param str subdirectory: The subdirectory of the prefix path
        :returns: The relative path to the created hook script
        :rtype: Path
        """
        raise NotImplementedError()

    def create_hook_include_file(
        self, env_hook_name, prefix_path, pkg_name, relative_path,
    ):
        """
        Create a hook script to include another script.

        This method must be overridden in a subclass.

        :param str env_hook_name: The name of the hook script
        :param Path prefix_path: The path of the install prefix
        :param str pkg_name: The package name
        :param str relative_path: The path of the included scripts
        :returns: The relative path to the created hook script
        :rtype: Path
        """
        raise NotImplementedError()

    async def generate_command_environment(
        self, task_name, build_base, dependencies,
    ):
        """
        Get the environment variables to invoke commands.

        The method must be overridden in a subclass if and only if the shell
        extension represents a "primary" shell (as defined in
        :attribute:`ShellExtensionPoint.PRIORITY`).

        :param str task_name: The name of the task
        :param Path build_base: The base path of the build directory
        :param set dependencies: The name of the recursive dependencies
        :returns: The environment
        :rtype: dict
        :raises SkipExtensionException: if the shell is not usable on the
          current platform
        """
        raise NotImplementedError()


def get_shell_extensions():
    """
    Get the available shell extensions.

    The extensions are grouped by their priority and each group is ordered by
    the entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.SHELL_NAME = name
    return order_extensions_grouped_by_priority(extensions)


async def get_command_environment(task_name, build_base, dependencies):
    """
    Get the environment variables to invoke commands.

    :param str task_name: The task name identifying a group of task extensions
    :param str build_base: The path of the build base
    :param dependencies: The ordered dictionary mapping dependency names to
      their paths
    """
    extensions = get_shell_extensions()
    for priority in extensions.keys():
        extensions_same_prio = extensions[priority]
        for extension in extensions_same_prio.values():
            try:
                # use the environment of the first successful shell extension
                return await extension.generate_command_environment(
                    task_name, Path(build_base), dependencies)
            except NotImplementedError:
                # skip extension, continue with next one
                logger.debug(
                    "Skip shell extension '{extension.SHELL_NAME}' for "
                    'command environment'.format_map(locals()))
            except SkipExtensionException as e:
                # skip extension, continue with next one
                logger.info(
                    "Skip shell extension '{extension.SHELL_NAME}' for "
                    'command environment: {e}'.format_map(locals()))
            except (CancelledError, RuntimeError):
                # re-raise same exception to handle it in the executor
                # without a traceback
                raise
            except Exception as e:
                # catch exceptions raised in shell extension
                exc = traceback.format_exc()
                logger.error(
                    'Exception in shell extension '
                    "'{extension.SHELL_NAME}': {e}\n{exc}"
                    .format_map(locals()))
                # skip failing extension, continue with next one
    raise RuntimeError(
        'Could not find a shell extension for the command environment')


async def get_environment_variables(cmd, *, cwd=None, shell=True):
    """
    Get the environment variables from the output of the command.

    :param args: the sequence of program arguments
    :param cwd: the working directory for the subprocess
    :param shell: whether to use the shell as the program to execute
    :rtype: dict
    """
    output = await check_output(cmd, cwd=cwd, shell=shell)
    env = {}
    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        parts = line.decode().split('=', 1)
        if len(parts) != 2:
            # skip lines which don't contain an equal sign
            continue
        env[parts[0]] = parts[1]
    assert len(env) > 0, "The environment shouldn't be empty"
    return env


def create_environment_hook(
    env_hook_name, prefix_path, pkg_name, name, subdirectory, *, mode='prepend'
):
    """
    Create a hook script for each primary shell.

    :param str env_hook_name: The name of the hook script
    :param Path prefix_path: The path of the install prefix
    :param str pkg_name: The package name
    :param str name: The name of the environment variable
    :param str subdirectory: The value to be appended
    :param str mode: The mode how the new value should be combined with an
      existing value, currently only the value `prepend` is supported
    :returns: The relative paths to the created hook scripts
    :rtype: list
    """
    logger.log(
        1, "create_environment_hook('%s', '%s')" % (pkg_name, env_hook_name))

    hooks = []
    extensions = get_shell_extensions()
    for priority in extensions.keys():
        # only consider primary shell extensions
        if priority <= ShellExtensionPoint.PRIORITY:
            break

        extensions_same_prio = extensions[priority]
        for extension in extensions_same_prio.values():
            if mode == 'prepend':
                try:
                    hook = extension.create_hook_prepend_value(
                        env_hook_name, prefix_path, pkg_name, name,
                        subdirectory)
                    assert isinstance(hook, Path), \
                        'create_hook_prepend_value() should return a Path ' \
                        'object'

                except Exception as e:
                    # catch exceptions raised in shell extension
                    exc = traceback.format_exc()
                    logger.error(
                        'Exception in shell extension '
                        "'{extension.SHELL_NAME}': {e}\n{exc}"
                        .format_map(locals()))
                    # skip failing extension, continue with next one
                    continue
                hooks.append(hook)
            else:
                raise NotImplementedError()
    if not hooks:
        raise RuntimeError(
            'Could not find a primary shell extension for creating an '
            'environment hook')
    return hooks


_get_colcon_prefix_path_warnings = set()


def get_colcon_prefix_path(*, skip):
    """
    Get the paths from the COLCON_PREFIX_PATH environment variable.

    For not existing paths a warning is being printed and the path is being
    skipped.
    Even for repeated invocation a warning is only being printed once for each
    non existing path.

    :param skip: The current prefix path to be skipped and not be included in
      the return value
    :returns: The list of prefix paths
    :rtype: list
    """
    global _get_colcon_prefix_path_warnings
    prefix_path = []
    colcon_prefix_path = os.environ.get('COLCON_PREFIX_PATH', '')
    for path in colcon_prefix_path.split(os.pathsep):
        if not path:
            continue
        if path == str(skip):
            continue
        if not os.path.exists(path):
            if path not in _get_colcon_prefix_path_warnings:
                logger.warn(
                    "The path '{path}' in the environment variable "
                    "COLCON_PREFIX_PATH doesn't exist".format_map(locals()))
                _get_colcon_prefix_path_warnings.add(path)
            continue
        prefix_path.append(path)
    return prefix_path
