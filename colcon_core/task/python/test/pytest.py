# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import sys

from _pytest.main import EXIT_NOTESTSCOLLECTED
from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.task import check_call
from colcon_core.task.python.test import has_test_dependency
from colcon_core.task.python.test import PythonTestingStepExtensionPoint
from colcon_core.verb.test import logger
from pkg_resources import iter_entry_points


class PytestPythonTestingStep(PythonTestingStepExtensionPoint):
    """Use `pytest` to test Python packages."""

    # use a higher priority than the default priority
    # in order to become the default
    PRIORITY = 200

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            PythonTestingStepExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

        entry_points = iter_entry_points('distutils.commands', name='pytest')
        if not list(entry_points):
            raise SkipExtensionException("'pytest-runner' not found")

    def add_arguments(self, *, parser):  # noqa: D102
        parser.add_argument(
            '--pytest-args',
            nargs='*', metavar='*', type=str.lstrip,
            help='Arbitrary arguments which are passed to all pytests '
            '(args which start with a dash must be prefixed with an escaped '
            'space `\ `, e.g.: `--pytest-args \ --showlocals`)')

    def match(self, context, env, setup_py_data):  # noqa: D102
        return has_test_dependency(setup_py_data, 'pytest')

    async def step(self, context, env, setup_py_data):  # noqa: D102
        cmd = [
            sys.executable,
            'setup.py', 'pytest',
            'egg_info', '--egg-base', context.args.build_base,
        ]
        args = [
            '--tb=short',
            '--junit-xml=' + os.path.join(
                context.args.build_base, 'pytest.xml'),
            '--junit-prefix=' + context.pkg.name,
            '-o cache_dir=' + os.path.join(context.args.build_base, '.cache'),
        ]
        env = dict(env)

        if has_test_dependency(setup_py_data, 'pytest-cov'):
            args += [
                '--cov=' + context.args.path,
                '--cov-report=html:' + os.path.join(
                    context.args.build_base, 'coverage.html'),
                '--cov-report=xml:' + os.path.join(
                    context.args.build_base, 'coverage.xml'),
                '--cov-branch',
            ]
            env['COVERAGE_FILE'] = os.path.join(
                context.args.build_base, '.coverage')

        if context.args.retest_until_fail:
            try:
                import pytest_repeat  # noqa: F401
            except ImportError:
                logger.warn(
                    "Ignored '--retest-until-fail' for package "
                    "'{context.pkg.name}' since the pytest extension 'repeat' "
                    'was not found'.format_map(locals()))
            else:
                count = context.args.retest_until_fail + 1
                args += [
                    '--count={count}'.format_map(locals()),
                ]

        if context.args.retest_until_pass:
            try:
                import pytest_rerunfailures  # noqa: F401
            except ImportError:
                logger.warn(
                    "Ignored '--retest-until-pass' for package "
                    "'{context.pkg.name}' since pytest extension "
                    "'rerunfailures' was not found".format_map(locals()))
            else:
                args += [
                    '--reruns={context.args.retest_until_pass}'
                    .format_map(locals()),
                ]

        if context.args.pytest_args is not None:
            args += context.args.pytest_args

        if args:
            env['PYTEST_ADDOPTS'] = ' '.join(args)
        rc = await check_call(context, cmd, cwd=context.args.path, env=env)
        if rc and rc.returncode != EXIT_NOTESTSCOLLECTED:
            return rc.returncode
