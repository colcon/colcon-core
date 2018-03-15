# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import sys

from colcon_core import shell
from colcon_core.environment import EnvironmentExtensionPoint
from colcon_core.environment import logger
from colcon_core.plugin_system import satisfies_version


class PathEnvironment(EnvironmentExtensionPoint):
    """Extend the `PATH` variable to find executables."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EnvironmentExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def create_environment_hooks(self, prefix_path, pkg_name):  # noqa: D102
        hooks = self._create_environment_hooks(prefix_path, pkg_name, 'bin')
        if sys.platform == 'win32':
            hooks += self._create_environment_hooks(
                prefix_path, pkg_name, 'Scripts', '-scripts')
        return hooks

    def _create_environment_hooks(
        self, prefix_path, pkg_name, subdirectory, suffix=''
    ):
        hooks = []
        bin_path = prefix_path / subdirectory
        logger.log(1, "checking '%s'" % bin_path)
        try:
            names = os.listdir(str(bin_path))
        except FileNotFoundError:
            pass
        else:
            for name in names:
                if not (bin_path / name).is_file():
                    continue
                hooks += shell.create_environment_hook(
                    'path' + suffix, prefix_path, pkg_name, 'PATH',
                    subdirectory, mode='prepend')
                break

        return hooks
