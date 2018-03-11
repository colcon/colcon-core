# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os

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
        hooks = []

        bin_path = prefix_path / 'bin'
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
                    'path', prefix_path, pkg_name, 'PATH', 'bin',
                    mode='prepend')
                break

        return hooks
