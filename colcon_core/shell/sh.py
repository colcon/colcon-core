# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
import shutil
import sys

from colcon_core import shell
from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.shell import check_dependency_availability
from colcon_core.shell import get_colcon_prefix_path
from colcon_core.shell import get_environment_variables
from colcon_core.shell import logger
from colcon_core.shell import ShellExtensionPoint
from colcon_core.shell.template import expand_template


class ShShell(ShellExtensionPoint):
    """Generate `.sh` scripts to extend the environment."""

    # the priority needs to be higher than the default for primary shells
    PRIORITY = 200

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(ShellExtensionPoint.EXTENSION_POINT_VERSION, '^2.0')
        if sys.platform == 'win32' and not shell.use_all_shell_extensions:
            raise SkipExtensionException('Not used on Windows systems')

    def create_prefix_script(self, prefix_path, merge_install):  # noqa: D102
        prefix_env_path = prefix_path / 'local_setup.sh'
        logger.info("Creating prefix script '%s'" % prefix_env_path)
        expand_template(
            Path(__file__).parent / 'template' / 'prefix.sh.em',
            prefix_env_path,
            {
                'prefix_path': prefix_path,
                'python_executable': sys.executable,
                'merge_install': merge_install,
                'package_script_no_ext': 'package',
            })
        shutil.copy(
            str(self._get_prefix_util_path()),
            str(prefix_path / '_local_setup_util.py'))

        prefix_chain_env_path = prefix_path / 'setup.sh'
        logger.info(
            "Creating prefix chain script '%s'" % prefix_chain_env_path)
        expand_template(
            Path(__file__).parent / 'template' / 'prefix_chain.sh.em',
            prefix_chain_env_path,
            {
                'prefix_path': prefix_path,
                'colcon_prefix_path': get_colcon_prefix_path(skip=prefix_path),
                'prefix_script_no_ext': 'local_setup',
            })

    def create_package_script(
        self, prefix_path, pkg_name, hooks
    ):  # noqa: D102
        pkg_env_path = prefix_path / 'share' / pkg_name / 'package.sh'
        logger.info("Creating package script '%s'" % pkg_env_path)
        expand_template(
            Path(__file__).parent / 'template' / 'package.sh.em',
            pkg_env_path,
            {
                'prefix_path': prefix_path,
                'hooks': list(filter(
                    lambda hook: str(hook[0]).endswith('.sh'), hooks)),
            })

    def create_hook_prepend_value(
        self, env_hook_name, prefix_path, pkg_name, name, subdirectory,
    ):  # noqa: D102
        hook_path = prefix_path / 'share' / pkg_name / 'hook' / \
            ('%s.sh' % env_hook_name)
        logger.info("Creating environment hook '%s'" % hook_path)
        expand_template(
            Path(__file__).parent / 'template' / 'hook_prepend_value.sh.em',
            hook_path,
            {
                'name': name,
                'subdirectory': subdirectory,
            })
        return hook_path

    async def generate_command_environment(
        self, task_name, build_base, dependencies,
    ):  # noqa: D102
        if sys.platform == 'win32':
            raise SkipExtensionException('Not usable on Windows systems')

        # check if all dependencies are available
        # removes dependencies available in the environment from the parameter
        check_dependency_availability(
            dependencies, script_filename='package.sh')

        hook_path = build_base / ('colcon_command_prefix_%s.sh' % task_name)
        expand_template(
            Path(__file__).parent / 'template' / 'command_prefix.sh.em',
            hook_path,
            {'dependencies': dependencies})

        cmd = ['.', str(hook_path), '&&', 'env']
        env = await get_environment_variables(cmd, cwd=str(build_base))

        # write environment variables to file for debugging
        env_path = build_base / ('colcon_command_prefix_%s.sh.env' % task_name)
        with env_path.open('w') as h:
            for key in sorted(env.keys()):
                value = env[key]
                h.write('{key}={value}\n'.format_map(locals()))

        return env
