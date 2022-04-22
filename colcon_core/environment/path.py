# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import sys

from colcon_core import shell
from colcon_core.environment import EnvironmentExtensionPoint
from colcon_core.environment import logger
from colcon_core.plugin_system import satisfies_version
from colcon_core.python_install_path import get_python_install_path


def _has_file(path):
    logger.log(1, "checking '%s'" % path)

    if not path.is_dir():
        return False

    for child in path.iterdir():
        if child.is_file():
            return True
    return False


class PathEnvironment(EnvironmentExtensionPoint):
    """Extend the `PATH` variable to find executables."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EnvironmentExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def create_environment_hooks(self, prefix_path, pkg_name):  # noqa: D102
        return self._create_environment_hooks(prefix_path, pkg_name, 'bin')

    def _create_environment_hooks(
        self, prefix_path, pkg_name, subdirectory, suffix=''
    ):
        hooks = []
        bin_path = prefix_path / subdirectory

        if _has_file(bin_path):
            hooks += shell.create_environment_hook(
                'path' + suffix, prefix_path, pkg_name, 'PATH', subdirectory,
                mode='prepend')

        return hooks


class PythonScriptsPathEnvironment(EnvironmentExtensionPoint):
    """Extend the `PATH` variable to find python scripts."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EnvironmentExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def create_environment_hooks(self, prefix_path, pkg_name):  # noqa: D102
        hooks = []
        bin_path = get_python_install_path('scripts', {'base': prefix_path})
        logger.log(1, "checking '%s'" % bin_path)
        try:
            names = os.listdir(str(bin_path))
        except FileNotFoundError:
            return

        if _has_file(bin_path):
            rel_bin_path = bin_path.relative_to(prefix_path)
            hooks += shell.create_environment_hook(
                'pythonscriptspath' + suffix, prefix_path, pkg_name, 'PATH',
                str(rel_bin_path), mode='prepend')

        return hooks
