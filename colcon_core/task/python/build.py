# Copyright 2019 Dan Rose
# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from distutils.sysconfig import get_python_lib
import os
from pathlib import Path
import shutil
import sys

from colcon_core.environment import create_environment_hooks
from colcon_core.environment import create_environment_scripts
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import create_environment_hook
from colcon_core.shell import get_command_environment
from colcon_core.task import check_call
from colcon_core.task import TaskExtensionPoint

logger = colcon_logger.getChild(__name__)


class PythonBuildTask(TaskExtensionPoint):
    """Build Python packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(TaskExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    async def build(self, *, additional_hooks=None):  # noqa: D102
        pkg = self.context.pkg
        args = self.context.args

        logger.info(
            "Building Python package in '{args.path}'".format_map(locals()))

        try:
            env = await get_command_environment(
                'setup_py', args.build_base, self.context.dependencies)
        except RuntimeError as e:
            logger.error(str(e))
            return 1

        Path(args.install_base).mkdir(parents=True, exist_ok=True)
        shutil.rmtree(args.build_base)

        if args.symlink_install:
            # prepare build directory
            shutil.copytree(args.path, args.build_base, copy_function=os.symlink)

            # `setup.py develop|install` requires the python lib path to exist
            python_lib = os.path.join(
                args.install_base, self._get_python_lib(args))

            os.makedirs(python_lib, exist_ok=True)

            # and being in the PYTHONPATH
            env = dict(env)

            env['PYTHONPATH'] = python_lib + os.pathsep + env.get('PYTHONPATH', '')
            cmdargs = ['pip', 'install', '--editable', 'file:' + args.build_base, '--upgrade',
                       '--prefix', args.install_base, '--no-deps']
            await check_call(self.context, cmdargs, cwd=args.build_base, env=env)
        else:
            shutil.copytree(args.path, args.build_base)
            cmdargs = ['pip', 'install', 'file:' + str(args.path), '--upgrade',
                       '--prefix', args.install_base,
                       '--build', str(Path('.', args.build_base)), '--no-deps']
            await check_call(self.context, cmdargs, cwd=args.path, env=env)

        # explicitly add the build directory to the PYTHONPATH
        # to maintain the desired order
        # otherwise the path from the easy-install.pth (which is the build
        # directory) will be added to the PYTHONPATH implicitly
        # but behind potentially other directories from the PYTHONPATH
        if additional_hooks is None:
            additional_hooks = []
        additional_hooks += create_environment_hook(
            'pythonpath_develop', Path(args.build_base), pkg.name,
            'PYTHONPATH', args.build_base, mode='prepend')

        hooks = create_environment_hooks(args.install_base, pkg.name)
        create_environment_scripts(
            pkg, args, default_hooks=hooks, additional_hooks=additional_hooks)

    def _get_python_lib(self, args):
        path = get_python_lib(prefix=args.install_base)
        return os.path.relpath(path, start=args.install_base)
