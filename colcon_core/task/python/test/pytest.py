# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from pathlib import PurePosixPath
import sys

from colcon_core.event.test import TestFailure
from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from colcon_core.task import check_call
from colcon_core.task.python.test import has_test_dependency
from colcon_core.task.python.test import PythonTestingStepExtensionPoint
from colcon_core.verb.test import logger
from pkg_resources import iter_entry_points
from pkg_resources import parse_version


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
            help='Pass arguments to pytests. '
            'Arguments matching other options must be prefixed by a space,\n'
            'e.g. --pytest-args " --help"')

    def match(self, context, env, setup_py_data):  # noqa: D102
        return has_test_dependency(setup_py_data, 'pytest')

    async def step(self, context, env, setup_py_data):  # noqa: D102
        cmd = [
            sys.executable,
            'setup.py', 'pytest',
            'egg_info', '--egg-base', context.args.build_base,
        ]
        junit_xml_path = Path(
            context.args.test_result_base
            if context.args.test_result_base
            else context.args.build_base) / 'pytest.xml'
        # avoid using backslashes in the PYTEST_ADDOPTS env var on Windows
        args = [
            '--tb=short',
            '--junit-xml=' + str(PurePosixPath(*junit_xml_path.parts)),
            '--junit-prefix=' + context.pkg.name,
        ]
        # use -o option only when available
        # https://github.com/pytest-dev/pytest/blob/3.3.0/CHANGELOG.rst
        from pytest import __version__ as pytest_version
        if parse_version(pytest_version) >= parse_version('3.3.0'):
            args += [
                '-o', 'cache_dir=' + str(PurePosixPath(
                    *(Path(context.args.build_base).parts)) / '.pytest_cache'),
            ]
        env = dict(env)

        if has_test_dependency(setup_py_data, 'pytest-cov'):
            args += [
                '--cov=' + str(PurePosixPath(
                    *(Path(context.args.path).parts))),
                '--cov-report=html:' + str(PurePosixPath(
                    *(Path(context.args.build_base).parts)) / 'coverage.html'),
                '--cov-report=xml:' + str(PurePosixPath(
                    *(Path(context.args.build_base).parts)) / 'coverage.xml'),
            ]
            # use --cov-branch option only when available
            # https://github.com/pytest-dev/pytest-cov/blob/v2.5.0/CHANGELOG.rst
            from pytest_cov import __version__ as pytest_cov_version
            if parse_version(pytest_cov_version) >= parse_version('2.5.0'):
                args += [
                    '--cov-branch',
                ]
            env['COVERAGE_FILE'] = os.path.join(
                context.args.build_base, '.coverage')

        if context.args.retest_until_fail:
            try:
                import pytest_repeat  # noqa: F401
            except ImportError:
                logger.warning(
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
                logger.warning(
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
            env['PYTEST_ADDOPTS'] = ' '.join(
                a if ' ' not in a else '"{a}"'.format_map(locals())
                for a in args)

        # create dummy result in case the invocation fails early
        # and doesn't generate a result file at all
        junit_xml_path.parent.mkdir(parents=True, exist_ok=True)
        junit_xml_path.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="{context.pkg.name}" tests="1" failures="1" time="0" errors="0" skip="0">
  <testcase classname="{context.pkg.name}" name="pytest.missing_result" status="run" time="0">
    <failure message="The test invocation failed without generating a result file."/>
  </testcase>
</testsuite>
""".format_map(locals()))  # noqa: E501

        rc = await check_call(context, cmd, cwd=context.args.path, env=env)

        # use local import to avoid a dependency on pytest
        from _pytest.main import EXIT_TESTSFAILED
        if rc and rc.returncode == EXIT_TESTSFAILED:
            context.put_event_into_queue(
                TestFailure(context.pkg.name))

        from _pytest.main import EXIT_NOTESTSCOLLECTED
        if rc and rc.returncode not in (
            EXIT_NOTESTSCOLLECTED, EXIT_TESTSFAILED
        ):
            return rc.returncode
