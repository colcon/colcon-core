# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from contextlib import suppress
with suppress(ImportError):
    # needed before importing distutils
    # to avoid warning introduced in setuptools 49.2.0
    import setuptools  # noqa: F401
from distutils.sysconfig import get_python_lib
from pathlib import Path

from colcon_core import shell
from colcon_core.environment import EnvironmentExtensionPoint
from colcon_core.environment import logger
from colcon_core.plugin_system import satisfies_version


class PythonPathEnvironment(EnvironmentExtensionPoint):
    """Extend the `PYTHONPATH` variable to find Python modules."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EnvironmentExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def create_environment_hooks(self, prefix_path, pkg_name):  # noqa: D102
        hooks = []

        python_path = Path(get_python_lib(prefix=str(prefix_path)))
        logger.log(1, "checking '%s'" % python_path)
        if python_path.exists():
            rel_python_path = python_path.relative_to(prefix_path)
            hooks += shell.create_environment_hook(
                'pythonpath', prefix_path, pkg_name,
                'PYTHONPATH', str(rel_python_path), mode='prepend')

        return hooks
