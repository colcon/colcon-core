# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import argparse
import datetime
import logging
from pathlib import Path
import signal
import sys
import traceback

from colcon_core.argument_parser import decorate_argument_parser
from colcon_core.entry_point import load_entry_points
from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.location import create_log_path
from colcon_core.location import get_config_path
from colcon_core.location import get_log_path
from colcon_core.location import set_default_config_path
from colcon_core.location import set_default_log_path
from colcon_core.logging import add_file_handler
from colcon_core.logging import colcon_logger  # noqa: F401
from colcon_core.logging import get_numeric_log_level
from colcon_core.logging import set_logger_level_from_env
from colcon_core.plugin_system import get_first_line_doc
from colcon_core.verb import get_verb_extensions

"""Environment variable to set the log level"""
LOG_LEVEL_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_LOG_LEVEL',
    'Set the log level (debug|10, info|20, warn|30, error|40, critical|50, or '
    'any other positive numeric value)')

"""Environment variable to set the configuration directory"""
HOME_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_HOME',
    'Set the configuration directory (default: ~/.colcon)')

"""Environment variable to set the log directory"""
LOG_PATH_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_LOG_PATH',
    'Set the log directory (default: $COLCON_HOME/log)')


def main(*, command_name='colcon', argv=None):
    """
    Execute the main logic of the command.

    The overview of the process:
    * Configure logging level based on an environment variable
    * Configure the configuration path
    * Create the argument parser

      * Document all environment variables
      * Decorate the parsers with additional functionality
      * Add the available verbs and their arguments

    * Configure logging level based on an arguments
    * Create an invocation specific log directory
    * Invoke the logic of the selected verb (if applicable)

    :param str command_name: The name of the command invoked
    :param list argv: The list of arguments
    :returns: The return code
    """
    global colcon_logger
    # default log level
    colcon_logger.setLevel(logging.WARN)
    set_logger_level_from_env(
        colcon_logger, '{command_name}_LOG_LEVEL'.format_map(locals()).upper())
    colcon_logger.debug(
        'Command line arguments: {argv}'
        .format(argv=argv if argv is not None else sys.argv))

    # set default locations for config files
    set_default_config_path(
        path=(
            Path('~') / '.{command_name}'.format_map(locals())).expanduser(),
        env_var='{command_name}_HOME'.format_map(locals()).upper())

    parser = create_parser('colcon_core.environment_variable')

    # get verb extensions and let them add their arguments
    verb_extensions = get_verb_extensions()
    add_subparsers(
        parser, command_name, verb_extensions, attribute='verb_name')

    args = parser.parse_args(args=argv)
    context = CommandContext(command_name=command_name, args=args)

    if args.log_level:
        colcon_logger.setLevel(args.log_level)

    colcon_logger.debug(
        'Parsed command line arguments: {args}'.format_map(locals()))

    # error: no verb provided
    if args.verb_name is None:
        print(parser.format_usage())
        return 'Error: No verb provided'

    # set default locations for log files
    now = datetime.datetime.now()
    now_str = str(now)[:-7].replace(' ', '_').replace(':', '-')
    set_default_log_path(
        base_path=get_config_path() / 'log',
        env_var='{command_name}_LOG_PATH'.format_map(locals()).upper(),
        subdirectory='{args.verb_name}_{now_str}'.format_map(locals()))

    # add a file handler writing all levels
    create_log_path(args.verb_name)
    handler = add_file_handler(
        colcon_logger, get_log_path() / 'logger_all.log')
    # write previous log messages to the file handler
    log_record = colcon_logger.makeRecord(
        colcon_logger.name, logging.DEBUG, __file__, 0,
        'Command line arguments: {argv}'
        .format(argv=argv if argv is not None else sys.argv),
        None, None)
    handler.handle(log_record)
    log_record = colcon_logger.makeRecord(
        colcon_logger.name, logging.DEBUG, __file__, 0,
        'Parsed command line arguments: {args}'.format_map(locals()),
        None, None)
    handler.handle(log_record)

    # invoke verb
    return verb_main(context, colcon_logger)


def create_parser(environment_variables_group_name):
    """
    Create the argument parser.

    It uses a custom raw description help formatter to maintain newlines.
    It uses the available argument parser extensions to decorate the parsers.
    It enumerates the registered environment variables in the epilog of the
    help message.

    :param str environment_variables_group_name: The entry point group name for
      the environment variable extensions
    :returns: The argument parser
    """
    # top level parser
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        epilog=get_environment_variables_epilog(
            environment_variables_group_name))

    # enable introspecting and intercepting all command line arguments
    parser = decorate_argument_parser(parser)

    add_log_level_argument(parser)

    return parser


class CustomFormatter(argparse.RawDescriptionHelpFormatter):
    """A custom formatter to maintain newlines."""

    def _split_lines(self, text, width):
        """Maintain newlines when the text starts with 'r|'."""
        lines = []
        for line in text.splitlines():
            if len(line) <= width:
                lines.append(line)
            else:
                lines += super()._split_lines(line, width)
        return lines


def get_environment_variables_epilog(group_name):
    """
    Get a message enumerating the registered environment variables.

    :param str group_name: The entry point group name for the environment
      variable extensions
    :returns: The message for the argument parser epilog
    :rtype: str
    """
    # list environment variables with descriptions
    entry_points = load_entry_points(group_name)
    env_vars = {
        env_var.name: env_var.description for env_var in entry_points.values()}
    epilog_lines = []
    for name in sorted(env_vars.keys()):
        epilog_lines += _format_pair(name, env_vars[name], indent=2, align=24)
    return 'Environment variables:\n' + '\n'.join(epilog_lines)


def add_log_level_argument(parser):
    """
    Add the argument for the log level to the parser.

    :param parser: The argument parser
    """
    parser.add_argument(
        '--log-level', action=LogLevelAction,
        help='Set log level for the console output, either by numeric or '
             'string value (default: warn)')


class LogLevelAction(argparse.Action):
    """Accept either positive integers or known log level names."""

    def __init__(self, option_strings, dest, *, nargs=None, **kwargs):
        """See :class:`argparse.Action.__init__`."""
        if nargs is not None:  # pragma: no cover
            raise ValueError('nargs not allowed')
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """See :class:`argparse.Action.__call__`."""
        try:
            value = get_numeric_log_level(values)
        except ValueError as e:
            parser.error(
                '{option_string} has unsupported value, {e}'
                .format_map(locals()))
        setattr(namespace, self.dest, value)


def add_subparsers(parser, cmd_name, verb_extensions, *, attribute):
    """
    Create argparse subparsers for each verb.

    The `cmd_name` is used for the title and description of the
    `add_subparsers` function call.

    For each verb extension a subparser is created.
    If the extension has an `add_arguments` method it is being called with the
    subparser being passed as the only argument.

    :param parser: The argument parser for this command
    :param str cmd_name: The name of the command to which the verbs are being
      added
    :param dict verb_extensions: The verb extensions indexed by the verb name
    :returns: The subparsers indexed by the verb name
    :rtype: dict
    """
    global colcon_logger
    assert verb_extensions, 'No verb extensions'

    # list of available verbs with their descriptions
    verbs = []
    for name, extension in verb_extensions.items():
        verbs += _format_pair(
            name, get_first_line_doc(extension), indent=0, align=22)

    # add subparser with description of verb extensions
    subparser = parser.add_subparsers(
        title='{cmd_name} verbs'.format_map(locals()),
        description='\n'.join(verbs),
        dest=attribute,
        help='call `{cmd_name} VERB -h` for specific help'
             .format_map(locals())
    )

    # add verb specific group and arguments
    for name, extension in verb_extensions.items():
        verb_parser = subparser.add_parser(
            getattr(extension, attribute.upper()),
            description=get_first_line_doc(extension) + '.',
            formatter_class=parser.formatter_class,
        )
        verb_parser.set_defaults(main=extension.main)
        if hasattr(extension, 'add_arguments'):
            try:
                retval = extension.add_arguments(parser=verb_parser)
                assert retval is None, 'add_arguments() should return None'
            except Exception as e:
                # catch exceptions raised in verb extension
                exc = traceback.format_exc()
                colcon_logger.error(
                    "Exception in verb extension '{extension.VERB_NAME}': "
                    '{e}\n{exc}'.format_map(locals()))
                # skip failing extension, continue with next one


def _format_pair(key, value, *, indent, align):
    """
    Format a key value pair to align with others printed by argparse.

    :param str key: The key
    :param str value: The value
    :param int indent: The indentation level of the key
    :param int align: The indentation level of the value
    :returns: The indented and potentially wrapped line(s)
    :rtype: str
    """
    lines = []
    prefix = ' ' * indent + key
    # wrap between key and value if the gap between them is smaller than this
    minimum_gap = 2
    if len(prefix) + minimum_gap <= align:
        # key fits in the same line as the value
        lines.append(prefix + ' ' * (align - len(prefix)))
    else:
        # the key is too long, the value needs to start on the next line
        lines.append(prefix)
        lines.append(' ' * align)

    # wrap between key and value if the gap between them is smaller than this
    maximum_line_length = 80
    maximum_value_length = maximum_line_length - align
    while value:
        if len(value) > maximum_value_length:
            try:
                # look for a space within the desired length
                i = value.rindex(' ', 0, maximum_value_length)
            except ValueError:
                # no space to wrap, just append everything in a single line
                pass
            else:
                # append part to last line
                lines[-1] += value[0:i]
                value = value[i + 1:].lstrip()
                # start a new line with the spaces for the alignment
                lines.append(' ' * align)
                continue

        # either the remaining value is short enough or no space was found
        lines[-1] += value
        break
    return lines


class CommandContext:
    """The context providing the command name and the parsed arguments."""

    __slots__ = ('command_name', 'args')

    def __init__(self, *, command_name: str, args: object):  # noqa: D107
        self.command_name = command_name
        self.args = args


def verb_main(context, logger):
    """
    Invoke the logic of the selected verb.

    If the invocation is interrupted the returned error code is
    `signal.SIGINT`.
    If the verb raises a `RuntimeException` an error message is logged which
    contains the message of the exception.
    For any other exception a traceback is included in the logged error
    message.

    :param context: The :class:`CommandContext`
    :param logger: The logger
    :returns: The return code
    """
    # call the extension's main method
    try:
        # catch exceptions raised in verb extension
        rc = context.args.main(context=context)
    except KeyboardInterrupt:
        rc = signal.SIGINT
    except RuntimeError as e:
        # only log the error message for "known" exceptions
        logger.error(
            '{context.command_name} {context.args.verb_name}: {e}'
            .format_map(locals()))
        return 1
    except Exception as e:
        # log the error message and a traceback for "unexpected" exceptions
        exc = traceback.format_exc()
        logger.error(
            '{context.command_name} {context.args.verb_name}: {e}\n{exc}'
            .format_map(locals()))
        return 1
    return rc
