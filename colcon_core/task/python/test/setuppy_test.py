# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from sys import executable

from colcon_core.plugin_system import satisfies_version
from colcon_core.task import check_call
from colcon_core.task.python.test import PythonTestingStepExtensionPoint
from colcon_core.verb.test import logger


class SetuppyPythonTestingStep(PythonTestingStepExtensionPoint):
    """Use `setup.py test` to test packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            PythonTestingStepExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def match(self, context, env, setup_py_data):  # noqa: D102
        return True

    async def step(self, context, env, setup_py_data):  # noqa: D102
        if context.args.retest_until_fail:
            logger.warning(
                "Ignored '--retest-until-fail' for package "
                "'{context.pkg.name}' since 'setup.py test' does not support "
                'the usage'.format_map(locals()))

        if context.args.retest_until_pass:
            logger.warning(
                "Ignored '--retest-until-pass' for package "
                "'{context.pkg.name}' since 'setup.py test' does not support "
                'the usage'.format_map(locals()))

        cmd = [
            executable,
            'setup.py', 'test',
            'egg_info', '--egg-base', context.args.build_base,
        ]
        rc = await check_call(context, cmd, cwd=context.args.path, env=env)
        if rc and rc.returncode:
            return rc.returncode
