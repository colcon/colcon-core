# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import signal

from colcon_core.command import CommandContext
from colcon_core.command import main
from colcon_core.command import verb_main
from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.verb import VerbExtensionPoint
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


class Extension1(VerbExtensionPoint):
    pass


class Extension2:
    """Very long line so that the help text needs to be wrapped."""

    def main(self, *, context):
        pass  # pragma: no cover


class Extension3(VerbExtensionPoint):

    def add_arguments(self, *, parser):
        raise RuntimeError('custom exception')


def test_main():
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        with patch(
            'colcon_core.argument_parser.get_argument_parser_extensions',
            return_value={}
        ):
            with pytest.raises(SystemExit) as e:
                main(argv=['--log-level', 'invalid'])
            assert e.value.code == 2

            main(argv=['--log-level', 'info'])

            with pytest.raises(SystemExit) as e:
                main(argv=['--help'])
            assert e.value.code == 0

            with patch(
                'colcon_core.command.load_entry_points',
                return_value={
                    'key1': EnvironmentVariable('name', 'description'),
                    'key2': EnvironmentVariable(
                        'extra_long_name_to_wrap help',
                        'extra long description text to require a wrap of the '
                        'help text not_only_on_spaces_but_also_forced_within_'
                        'a_very_long_consecutive_word'),
                }
            ):
                main(argv=['extension1'])


class Object(object):
    pass


def test_verb_main():
    args = Object()
    args.verb_name = 'verb_name'
    logger = Object()
    logger.error = Mock()

    # pass through return code
    args.main = Mock(return_value=42)
    context = CommandContext(command_name='command_name', args=args)
    rc = verb_main(context, logger)
    assert rc == args.main.return_value
    logger.error.assert_not_called()

    # catch KeyboardInterrupt and return SIGINT error code
    args.main.side_effect = KeyboardInterrupt()
    rc = verb_main(context, logger)
    assert rc == signal.SIGINT
    logger.error.assert_not_called()

    # catch RuntimeError and output error message
    args.main.side_effect = RuntimeError('known error condition')
    rc = verb_main(context, logger)
    assert rc
    logger.error.assert_called_once_with(
        'command_name verb_name: known error condition')
    logger.error.reset_mock()

    # catch Exception and output error message including traceback
    args.main.side_effect = Exception('custom error message')
    rc = verb_main(context, logger)
    assert rc
    assert logger.error.call_count == 1
    assert len(logger.error.call_args[0]) == 1
    assert logger.error.call_args[0][0].startswith(
        'command_name verb_name: custom error message\n')
    assert 'Exception: custom error message' in logger.error.call_args[0][0]
