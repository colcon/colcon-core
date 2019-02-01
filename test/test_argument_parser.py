# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from argparse import ArgumentParser

from colcon_core.argument_parser import ArgumentParserDecorator
from colcon_core.argument_parser import ArgumentParserDecoratorExtensionPoint
from colcon_core.argument_parser import decorate_argument_parser
from colcon_core.argument_parser import get_argument_parser_extensions
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


class Extension1(ArgumentParserDecoratorExtensionPoint):
    PRIORITY = 80


class Extension2(ArgumentParserDecoratorExtensionPoint):
    pass


def test_get_argument_parser_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_argument_parser_extensions()
        assert ['extension2', 'extension1'] == \
            list(extensions.keys())


def decorate_argument_parser_mock(*, parser):
    class Decorator():

        def __init__(self, parser):
            self.parser = parser

        def add_argument(self, *args, **kwargs):
            pass  # pragma: no cover
    return Decorator(parser)


def test_decorate_argument_parser():
    parser = ArgumentParser()
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_argument_parser_extensions()

        # one invalid return value, one not implemented
        extensions['extension1'].decorate_argument_parser = Mock(
            return_value=None)
        with patch('colcon_core.argument_parser.logger.error') as error:
            decorated_parser = decorate_argument_parser(parser)
        assert decorated_parser == parser
        # the raised exceptions are catched and result in error messages
        assert error.call_count == 2
        assert len(error.call_args_list[0][0]) == 1
        assert error.call_args_list[0][0][0].startswith(
            "Exception in argument parser decorator extension 'extension2': "
            '\n')
        assert error.call_args_list[0][0][0].endswith(
            '\nNotImplementedError\n')
        assert len(error.call_args_list[1][0]) == 1
        assert error.call_args_list[1][0][0].startswith(
            "Exception in argument parser decorator extension 'extension1': "
            'decorate_argument_parser() should return a parser like object\n')

        # one exception, one valid decorator
        extensions['extension2'].decorate_argument_parser = Mock(
            side_effect=RuntimeError('custom exception'))
        extensions['extension1'].decorate_argument_parser = Mock(
            side_effect=decorate_argument_parser_mock)
        with patch('colcon_core.argument_parser.logger.error') as error:
            decorated_parser = decorate_argument_parser(parser)
        assert decorated_parser.parser == parser
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].startswith(
            "Exception in argument parser decorator extension 'extension2': "
            'custom exception\n')


class Decorator(ArgumentParserDecorator):

    def __init__(self, parser, **kwargs):
        self.foo = 'foo'
        super().__init__(parser, **kwargs)


def test_argument_parser_decorator():
    parser = ArgumentParser()

    # __getattr__
    decorator = ArgumentParserDecorator(parser)
    assert decorator.add_argument == parser.add_argument

    del decorator.__dict__['_parser']
    with pytest.raises(AttributeError):
        decorator.add_argument

    # __setattr__
    decorator = Decorator(parser)
    decorator.foo = 'bar'
    assert 'foo' in decorator.__dict__
    assert decorator.__dict__['foo'] == 'bar'

    decorator.add_argument = True
    assert parser.add_argument is True

    assert 'bar' not in decorator.__dict__
    del decorator.__dict__['_parser']
    decorator.bar = 'baz'
    assert 'bar' in decorator.__dict__
    assert decorator.__dict__['bar'] == 'baz'

    # nesting
    parser = ArgumentParser()
    decorator = Decorator(parser)
    group = decorator.add_argument_group()
    group.add_argument('arg1')

    group = decorator.add_mutually_exclusive_group()
    group.add_argument('--arg2', action='store_true')

    group = decorator.add_subparsers(dest='verb')
    group = group.add_parser('do')
    group.add_argument('arg3')

    args = parser.parse_args(['ARG1', '--arg2', 'do', 'ARG3'])
    assert args.arg1 == 'ARG1'
    assert args.arg2 is True
    assert args.verb == 'do'
    assert args.arg3 == 'ARG3'
