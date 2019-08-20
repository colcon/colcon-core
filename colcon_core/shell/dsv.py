# Copyright 2019 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path

from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import logger
from colcon_core.shell import ShellExtensionPoint
from colcon_core.shell.template import expand_template


class DsvShell(ShellExtensionPoint):
    """Generate `.dsv` files describing the intended environment change."""

    # the priority needs to be higher than the default for primary shells
    PRIORITY = 200

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(ShellExtensionPoint.EXTENSION_POINT_VERSION, '^2.0')

    def create_prefix_script(self, prefix_path, merge_install):  # noqa: D102
        pass

    def create_package_script(
        self, prefix_path, pkg_name, hooks
    ):  # noqa: D102
        pkg_env_path = prefix_path / 'share' / pkg_name / 'package.dsv'
        logger.info("Creating package descriptor '%s'" % pkg_env_path)
        expand_template(
            Path(__file__).parent / 'template' / 'package.dsv.em',
            pkg_env_path,
            {
                'hooks': hooks,
            })

    def create_hook_prepend_value(
        self, env_hook_name, prefix_path, pkg_name, name, subdirectory,
    ):  # noqa: D102
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
