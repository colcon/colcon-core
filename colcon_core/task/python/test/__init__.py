# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import re
import traceback

from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import get_first_line_doc
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_priority
from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import get_command_environment
from colcon_core.task import TaskExtensionPoint
from colcon_core.task.python import get_setup_data

logger = colcon_logger.getChild(__name__)


class PythonTestTask(TaskExtensionPoint):
    """Test Python packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(TaskExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        add_python_testing_step_arguments(parser)

    async def test(self, *, additional_hooks=None):  # noqa: D102
        pkg = self.context.pkg
        args = self.context.args

        logger.info(
            "Testing Python package in '{args.path}'".format_map(locals()))

        try:
            env = await get_command_environment(
                'setup_py', args.build_base, self.context.dependencies)
        except RuntimeError as e:
            logger.error(str(e))
            return 1
        setup_py_data = get_setup_data(self.context.pkg, env)

        # select the step extension which should perform the python testing
        if args.python_testing:
            key = args.python_testing
            extension = get_python_testing_step_extension(key)
        else:
            extensions = get_python_testing_step_extensions()
            for key, extension in extensions.items():
                logger.log(
                    1, "test() by extension '{key}'".format_map(locals()))
                try:
                    matched = extension.match(self.context, env, setup_py_data)
                except Exception as e:
                    # catch exceptions raised in python testing step extension
                    exc = traceback.format_exc()
                    logger.error(
                        'Exception in Python testing step extension '
                        "'{extension.STEP_TYPE}': {e}\n{exc}"
                        .format_map(locals()))
                    # skip failing extension, continue with next one
                    continue
                if matched:
                    break
            else:
                logger.warning(
                    "No Python Testing Step extension matched in '{args.path}'"
                    .format_map(locals()))
                return

        logger.log(
            1, "test.step() by extension '{key}'".format_map(locals()))
        try:
            return await extension.step(self.context, env, setup_py_data)
        except Exception as e:
            # catch exceptions raised in python testing step extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in Python testing step extension '
                "'{extension.STEP_TYPE}': {e}\n{exc}".format_map(locals()))
            return 1


class PythonTestingStepExtensionPoint:
    """
    The interface for Python testing step extensions.

    A Python testing step extension performs testing of a Python package.

    For each instance the attribute `STEP_TYPE` is being set to the basename of
    the entry point registering the extension.
    """

    """The version of the Python testing step extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of Python testing step extensions."""
    PRIORITY = 100

    def add_arguments(self, *, parser):
        """
        Add command line arguments specific to the Python testing step.

        The method is intended to be overridden in a subclass.

        :param parser: The argument parser
        """
        pass

    def match(self, context, env, setup_py_data):
        """
        Determine if this instance claims to process the specific package.

        This method must be overridden in a subclass.

        :param context: The task context describing the package
        :param env: The environment dictionary
        :param setup_py_data: The data extracted from the setup.py file
        :returns: True if it claims to process the package, False otherwise
        :rtype: bool
        """
        raise NotImplementedError()

    async def step(self):
        """
        Execute the Python testing step logic.

        This method must be overridden in a subclass.

        :returns: The return code
        """
        raise NotImplementedError()


def get_python_testing_step_extensions():
    """
    Get the available Python testing step extensions.

    The extensions are ordered by their priority and entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(
        'colcon_core.python_testing', unique_instance=False)
    for name in list(extensions.keys()):
        extension = extensions[name]
        extension.STEP_TYPE = name
    return order_extensions_by_priority(extensions)


def add_python_testing_step_arguments(parser):
    """
    Add the command line arguments for the Python testing step extensions.

    :param parser: The argument parser
    """
    extensions = get_python_testing_step_extensions()
    descriptions = ''
    for key, extension in extensions.items():
        desc = get_first_line_doc(extension)
        if not desc:
            # show extensions without a description
            # to mention the available options
            desc = '<no description>'
        # it requires a custom formatter to maintain the newline
        descriptions += '\n* {key}: {desc}'.format_map(locals())

    parser.add_argument(
        '--python-testing', type=str, choices=sorted(extensions.keys()),
        help='The Python testing framework to use (default: determined '
             'based on the packages `tests_require`)'
             '{descriptions}'.format_map(locals()))

    for extension in extensions.values():
        try:
            retval = extension.add_arguments(parser=parser)
            assert retval is None, 'add_arguments() should return None'
        except Exception as e:
            # catch exceptions raised in package selection extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in Python testing step extension '
                "'{extension.STEP_TYPE}': {e}\n{exc}".format_map(locals()))
            # skip failing extension, continue with next one


def get_python_testing_step_extension(step_name):
    """
    Get a specific Python testing step extension.

    :param str step_name: The entry point name of the extension
    :returns: A unique instance of the extension, otherwise None
    """
    extensions = instantiate_extensions(
        'colcon_core.python_testing.' + step_name, unique_instance=True)
    if step_name not in extensions:
        return None
    extension = extensions[step_name]
    extension.STEP_NAME = step_name
    return extension


def has_test_dependency(setup_py_data, name):
    """
    Check if the package has a specific test dependency.

    :param dict setup_py_data: The meta information of the package
    :returns: True if the package has a test dependency on the given name,
      False otherwise
    :rtype: bool
    """
    tests_require = setup_py_data.get('tests_require', [])
    for d in tests_require:
        # the name might be followed by a version
        # separated by any of the following: ' ', <, >, <=, >=, ==, !=
        parts = re.split(r' |<|=|>|!', d)
        if parts[0] == name:
            return True
    return False
