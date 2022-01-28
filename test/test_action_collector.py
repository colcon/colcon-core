# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import argparse
import sys

from colcon_core.argument_parser.action_collector \
    import ActionCollectorDecorator
from colcon_core.argument_parser.action_collector \
    import SuppressRequiredActions
from colcon_core.argument_parser.action_collector \
    import SuppressTypeConversions
import pytest


class _RaisingArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        raise sys.exc_info()[1] or Exception(message)


def test_action_collector_decorator():
    parser = argparse.ArgumentParser()
    decorator = ActionCollectorDecorator(parser)
    a = decorator.add_argument('positional')
    assert decorator.get_collected_actions() == {a}

    b = decorator.add_argument('--option', type=bool)
    assert decorator.get_collected_actions() == {a, b}


def test_suppress_required_actions():
    parser = _RaisingArgumentParser()
    decorator = ActionCollectorDecorator(parser)
    pos1 = decorator.add_argument('pos1')
    decorator.add_argument('pos2', nargs='?')

    args = parser.parse_args(['foo', 'bar'])
    assert 'foo' == args.pos1
    assert 'bar' == args.pos2

    with SuppressRequiredActions((decorator,)):
        parser.parse_args([])
    with pytest.raises(Exception):
        parser.parse_args([])
    with pytest.raises(Exception):
        with SuppressRequiredActions((decorator,), {pos1}):
            parser.parse_args([])

    args = parser.parse_args(['foo', 'bar'])
    assert 'foo' == args.pos1
    assert 'bar' == args.pos2


def test_suppress_type_conversions():
    parser = _RaisingArgumentParser()
    decorator = ActionCollectorDecorator(parser)
    action_f = decorator.add_argument('-f', type=float)
    action_i = decorator.add_argument('-i', type=int)
    decorator.register('action', 'not_implemented', argparse.Action)
    decorator.register('type', 'hex', float.fromhex)
    action_x = decorator.add_argument('-x', type='hex', default=None)
    decorator.add_argument('-s')

    args = parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])
    assert 3.14 == args.f
    assert 1 == args.i
    assert 0x42 == args.x

    with SuppressTypeConversions((decorator,)):
        parser.parse_args(['-f', 'bar', '-i', '1', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(['-f', 'bar', '-i', '1', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        with SuppressTypeConversions((decorator,), {action_f}):
            parser.parse_args(['-f', 'bar', '-i', '1', '-x', '0x42'])

    with SuppressTypeConversions((decorator,)):
        parser.parse_args(['-f', '3.14', '-i', 'bar', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(['-f', '3.14', '-i', 'bar', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        with SuppressTypeConversions((decorator,), {action_i}):
            parser.parse_args(['-f', '3.14', '-i', 'bar', '-x', '0x42'])

    with SuppressTypeConversions((decorator,)):
        parser.parse_args(['-f', '3.14', '-i', '1', '-x', 'foo'])
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(['-f', '3.14', '-i', '1', '-x', 'foo'])
    with pytest.raises(argparse.ArgumentError):
        with SuppressTypeConversions((decorator,), {action_x}):
            parser.parse_args(['-f', '3.14', '-i', '1', '-x', 'foo'])

    args = parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])
    assert 3.14 == args.f
    assert 1 == args.i
    assert 0x42 == args.x


def test_suppress_required_actions_not_decorated():
    parser = _RaisingArgumentParser()
    parser.add_argument('pos1')
    parser.add_argument('pos2', nargs='?')

    args = parser.parse_args(['foo'])
    assert 'foo' == args.pos1
    with pytest.raises(Exception):
        parser.parse_args([])

    with SuppressRequiredActions((parser,)):
        args = parser.parse_args(['foo'])
    assert 'foo' == args.pos1
    with pytest.raises(Exception):
        with SuppressRequiredActions((parser,)):
            parser.parse_args([])

    args = parser.parse_args(['foo'])
    assert 'foo' == args.pos1
    with pytest.raises(Exception):
        parser.parse_args([])


def test_suppress_type_conversion_not_decorated():
    parser = _RaisingArgumentParser()
    parser.add_argument('-f', type=float)
    parser.add_argument('-i', type=int)
    parser.register('action', 'not_implemented', argparse.Action)
    parser.register('type', 'hex', float.fromhex)
    parser.add_argument('-x', type='hex', default=None)

    args = parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])
    assert 3.14 == args.f
    assert 1 == args.i
    assert 0x42 == args.x

    with SuppressTypeConversions((parser,)):
        parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])

    args = parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])
    assert 3.14 == args.f
    assert 1 == args.i
    assert 0x42 == args.x
