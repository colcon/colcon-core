# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import OrderedDict
import copy
import logging
import os
from pathlib import Path
import traceback

from colcon_core.argument_parser.destination_collector \
    import DestinationCollectorDecorator
from colcon_core.event_handler import add_event_handler_arguments
from colcon_core.executor import add_executor_arguments
from colcon_core.executor import execute_jobs
from colcon_core.executor import Job
from colcon_core.package_identification.ignore import IGNORE_MARKER
from colcon_core.package_selection import add_arguments \
    as add_packages_arguments
from colcon_core.package_selection import get_packages
from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import get_shell_extensions
from colcon_core.task import add_task_arguments
from colcon_core.task import get_task_extension
from colcon_core.task import TaskContext
from colcon_core.verb import check_and_mark_build_tool
from colcon_core.verb import check_and_mark_install_layout
from colcon_core.verb import logger
from colcon_core.verb import VerbExtensionPoint


class BuildPackageArguments:
    """Arguments to build a specific package."""

    def __init__(self, pkg, args, *, additional_destinations=None):
        """
        Constructor.

        :param pkg: The package descriptor
        :param args: The parsed command line arguments
        :param list additional_destinations: The destinations of additional
          arguments
        """
        super().__init__()
        self.path = os.path.abspath(
            os.path.join(os.getcwd(), str(pkg.path)))
        self.build_base = os.path.abspath(os.path.join(
            os.getcwd(), args.build_base, pkg.name))
        self.install_base = os.path.abspath(os.path.join(
            os.getcwd(), args.install_base))
        if not args.merge_install:
            self.install_base = os.path.join(
                self.install_base, pkg.name)
        self.symlink_install = args.symlink_install
        self.test_result_base = os.path.abspath(os.path.join(
            os.getcwd(), args.test_result_base, pkg.name)) \
            if args.test_result_base else None

        # set additional arguments from the command line or package metadata
        for dest in (additional_destinations or []):
            if hasattr(args, dest):
                update_object(
                    self, dest, getattr(args, dest),
                    pkg.name, 'command line')
            if dest in pkg.metadata:
                update_object(
                    self, dest, pkg.metadata[dest],
                    pkg.name, 'package metadata')


def update_object(object_, key, value, package_name, value_source):
    """
    Set or update an attribute of an object.

    If the attribute exists and the passed value as well as the current value
    of the attribute are dictionaries then the current values are being updated
    with the passed values.

    If the attribute exists and the passed value as well as the current value
    of the attribute are lists then the passed values are being appended to the
    current values.

    Otherwise the attribute is being set to the passed value potentially
    overwriting an existing value.

    :param key: The name of the attributes
    :param value: The value used to set or update the attribute
    :param str package_name: The package name, only used for log messages
    :param str value_source: The source of the value, only used for log
      messages
    """
    if not hasattr(object_, key):
        logger.log(
            5, "set package '{package_name}' build argument '{key}' from "
            "{value_source} to '{value}'".format_map(locals()))
        # add value to the object
        # copy value to avoid changes to either of them to affect each other
        setattr(object_, key, copy.deepcopy(value))
        return

    old_value = getattr(object_, key)
    if isinstance(old_value, dict) and isinstance(value, dict):
        logger.log(
            5, "update package '{package_name}' build argument '{key}' from "
            "{value_source} with '{value}'".format_map(locals()))
        # update dictionary
        old_value.update(value)
        return

    if isinstance(old_value, list) and isinstance(value, list):
        logger.log(
            5, "extend package '{package_name}' build argument '{key}' from "
            "{value_source} with '{value}'".format_map(locals()))
        # extend list
        old_value += value
        return

    severity = 5 \
        if old_value is None or type(old_value) == type(value) \
        else logging.WARNING
    logger.log(
        severity, "overwrite package '{package_name}' build argument '{key}' "
        "from {value_source} with '{value}' (before: '{old_value}')"
        .format_map(locals()))
    # overwrite existing value
    # copy value to avoid changes to either of them to affect each other
    setattr(object_, key, copy.deepcopy(value))


class BuildVerb(VerbExtensionPoint):
    """Build a set of packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(VerbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        parser.add_argument(
            '--build-base',
            default='build',
            help='The base path for all build directories (default: build)')
        parser.add_argument(
            '--install-base',
            default='install',
            help='The base path for all install prefixes (default: install)')
        parser.add_argument(
            '--merge-install',
            action='store_true',
            help='Merge all install prefixes into a single location')
        parser.add_argument(
            '--symlink-install',
            action='store_true',
            help='Use symlinks instead of copying files where possible')
        parser.add_argument(
            '--test-result-base',
            help='The base path for all test results (default: --build-base)')
        add_executor_arguments(parser)
        add_event_handler_arguments(parser)

        add_packages_arguments(parser)

        decorated_parser = DestinationCollectorDecorator(parser)
        add_task_arguments(decorated_parser, 'colcon_core.task.build')
        self.task_argument_destinations = decorated_parser.get_destinations()

    def main(self, *, context):  # noqa: D102
        check_and_mark_build_tool(context.args.build_base)
        check_and_mark_install_layout(
            context.args.install_base,
            merge_install=context.args.merge_install)

        self._create_paths(context.args)

        decorators = get_packages(
            context.args,
            additional_argument_names=self.task_argument_destinations,
            recursive_categories=('run', ))

        install_base = os.path.abspath(os.path.join(
            os.getcwd(), context.args.install_base))
        jobs = self._get_jobs(context.args, decorators, install_base)

        rc = execute_jobs(context, jobs)

        self._create_prefix_scripts(install_base, context.args.merge_install)

        return rc

    def _create_paths(self, args):
        self._create_path(args.build_base)
        self._create_path(args.install_base)

    def _create_path(self, path):
        path = Path(os.path.abspath(path))
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        ignore_marker = path / IGNORE_MARKER
        if not ignore_marker.exists():
            with ignore_marker.open('w'):
                pass

    def _get_jobs(self, args, decorators, install_base):
        jobs = OrderedDict()
        for decorator in decorators:
            if not decorator.selected:
                continue

            pkg = decorator.descriptor
            extension = get_task_extension('colcon_core.task.build', pkg.type)
            if not extension:
                logger.warning(
                    "No task extension to 'build' a '{pkg.type}' package"
                    .format_map(locals()))
                continue

            recursive_dependencies = OrderedDict()
            for dep_name in decorator.recursive_dependencies:
                dep_path = install_base
                if not args.merge_install:
                    dep_path = os.path.join(dep_path, dep_name)
                recursive_dependencies[dep_name] = dep_path

            package_args = BuildPackageArguments(
                pkg, args, additional_destinations=self
                .task_argument_destinations.values())
            ordered_package_args = ', '.join([
                ('%s: %s' % (repr(k), repr(package_args.__dict__[k])))
                for k in sorted(package_args.__dict__.keys())
            ])
            logger.debug(
                "Building package '{pkg.name}' with the following arguments: "
                '{{{ordered_package_args}}}'.format_map(locals()))
            task_context = TaskContext(
                pkg=pkg, args=package_args,
                dependencies=recursive_dependencies)

            job = Job(
                identifier=pkg.name,
                dependencies=set(recursive_dependencies.keys()),
                task=extension, task_context=task_context)

            jobs[pkg.name] = job
        return jobs

    def _create_prefix_scripts(self, install_base, merge_install):
        extensions = get_shell_extensions()
        for priority in extensions.keys():
            extensions_same_prio = extensions[priority]
            for extension in extensions_same_prio.values():
                try:
                    retval = extension.create_prefix_script(
                        Path(install_base), merge_install)
                    assert retval is None, \
                        'create_prefix_script() should return None'
                except Exception as e:
                    # catch exceptions raised in shell extension
                    exc = traceback.format_exc()
                    logger.error(
                        'Exception in shell extension '
                        "'{extension.SHELL_NAME}': {e}\n{exc}"
                        .format_map(locals()))
                    # skip failing extension, continue with next one
