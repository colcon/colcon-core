# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import shutil
import signal
import sys
from tempfile import mkdtemp
from tempfile import TemporaryDirectory
from unittest.mock import Mock
from unittest.mock import patch

from colcon_core.command import CommandContext
from colcon_core.command import create_parser
from colcon_core.command import get_prog_name
from colcon_core.command import main
from colcon_core.command import verb_main
from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.verb import VerbExtensionPoint
import pytest

from .extension_point_context import ExtensionPointContext


class Extension1(VerbExtensionPoint):
    pass


class Extension2:
    """Very long line so that the help text needs to be wrapped."""

    def main(self, *, context):
        pass  # pragma: no cover


class Extension3(VerbExtensionPoint):

    def add_arguments(self, *, parser):
        raise RuntimeError('custom exception')


@patch('colcon_core.output_style.get_output_style_extensions', dict)
def test_main():
    with ExtensionPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        with patch(
            'colcon_core.argument_parser.get_argument_parser_extensions',
            return_value={}
        ):
            with pytest.raises(SystemExit) as e:
                main(argv=['--help'])
            assert e.value.code == 0

            with pytest.raises(SystemExit) as e:
                main(argv=['--log-level', 'invalid'])
            assert e.value.code == 2

            # avoid creating log directory in the package directory
            log_base = mkdtemp(prefix='test_colcon_')
            argv = ['--log-base', log_base]
            try:
                main(argv=argv + ['--log-level', 'info'])

                with patch(
                    'colcon_core.command.load_extension_points',
                    return_value={
                        'key1': EnvironmentVariable('name', 'description'),
                        'key2': EnvironmentVariable(
                            'extra_long_name_to_wrap help',
                            'extra long description text to require a wrap of '
                            'the help text not_only_on_spaces_but_also_forced_'
                            'within_a_very_long_consecutive_word'),
                    }
                ):
                    main(argv=argv + ['extension1'])
            finally:
                # the logging subsystem might still have file handles pending
                # therefore only try to delete the temporary directory
                shutil.rmtree(log_base, ignore_errors=True)

        # catch KeyboardInterrupt and return SIGINT error code
        with patch('colcon_core.command._main', return_value=0) as _main:
            _main.side_effect = KeyboardInterrupt()
            rc = main()
            assert rc == signal.SIGINT


def test_main_no_verbs_or_env():
    with ExtensionPointContext():
        with patch(
            'colcon_core.command.load_extension_points',
            return_value={},
        ):
            with pytest.raises(SystemExit) as e:
                main(argv=['--help'])
            assert e.value.code == 0


def test_main_default_verb():
    with ExtensionPointContext():
        with patch(
            'colcon_core.argument_parser.get_argument_parser_extensions',
            return_value={}
        ):
            with pytest.raises(SystemExit) as e:
                main(argv=['--help'], default_verb=Extension1)
            assert e.value.code == 0

            with pytest.raises(SystemExit) as e:
                main(
                    argv=['--log-level', 'invalid'],
                    default_verb=Extension1)
            assert e.value.code == 2

            with patch.object(Extension1, 'main', return_value=0) as mock_main:
                assert not main(
                    argv=['--log-base', '/dev/null'],
                    default_verb=Extension1)
                mock_main.assert_called_once()


def test_create_parser():
    with ExtensionPointContext():
        parser = create_parser('colcon_core.environment_variable')

    parser.add_argument('--foo', nargs='*', type=str.lstrip)
    args = parser.parse_args(['--foo', '--bar', '--baz'])
    assert args.foo == ['--bar', '--baz']

    parser.add_argument('--baz', action='store_true')
    args = parser.parse_args(['--foo', '--bar', '--baz'])
    assert args.foo == ['--bar']
    assert args.baz is True

    args = parser.parse_args(['--foo', '--bar', ' --baz'])
    assert args.foo == ['--bar', '--baz']

    argv = sys.argv
    sys.argv = ['/some/path/prog_name/__main__.py'] + sys.argv[1:]
    with ExtensionPointContext():
        parser = create_parser('colcon_core.environment_variable')
    sys.argv = argv
    assert parser.prog == 'prog_name'


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


def test_prog_name_module():
    argv = [os.path.join('foo', 'bar', '__main__.py')]
    with patch('colcon_core.command.sys.argv', argv):
        # prog should be the module containing __main__.py
        assert get_prog_name() == 'bar'


def test_prog_name_on_path():
    # use __file__ since we know it exists
    argv = [__file__]
    with patch('colcon_core.command.sys.argv', argv):
        with patch(
            'colcon_core.command.shutil.which',
            return_value=__file__
        ):
            # prog should be shortened to the basename
            assert get_prog_name() == 'test_command.py'


def test_prog_name_not_on_path():
    # use __file__ since we know it exists
    argv = [__file__]
    with patch('colcon_core.command.sys.argv', argv):
        with patch('colcon_core.command.shutil.which', return_value=None):
            # prog should remain unchanged
            assert get_prog_name() == __file__


def test_prog_name_different_on_path():
    # use __file__ since we know it exists
    argv = [__file__]
    with patch('colcon_core.command.sys.argv', argv):
        with patch(
            'colcon_core.command.shutil.which',
            return_value=sys.executable
        ):
            # prog should remain unchanged
            assert get_prog_name() == __file__


def test_prog_name_not_a_file():
    # pick some file that doesn't actually exist on disk
    no_such_file = os.path.join(__file__, 'foobar')
    argv = [no_such_file]
    with patch('colcon_core.command.sys.argv', argv):
        with patch(
            'colcon_core.command.shutil.which',
            return_value=no_such_file
        ):
            # prog should remain unchanged
            assert get_prog_name() == no_such_file


@pytest.mark.skipif(sys.platform == 'win32', reason='Symlinks not supported.')
def test_prog_name_symlink():
    # use __file__ since we know it exists
    with TemporaryDirectory(prefix='test_colcon_') as temp_dir:
        linked_file = os.path.join(temp_dir, 'test_command.py')
        os.symlink(__file__, linked_file)

        argv = [linked_file]
        with patch('colcon_core.command.sys.argv', argv):
            with patch(
                'colcon_core.command.shutil.which',
                return_value=__file__
            ):
                # prog should be shortened to the basename
                assert get_prog_name() == 'test_command.py'


@pytest.mark.skipif(sys.platform != 'win32', reason='Only valid on Windows.')
def test_prog_name_easy_install():
    # use __file__ since we know it exists
    argv = [__file__[:-3]]
    with patch('colcon_core.command.sys.argv', argv):
        with patch(
            'colcon_core.command.shutil.which',
            return_value=__file__
        ):
            # prog should be shortened to the basename
            assert get_prog_name() == 'test_command'
