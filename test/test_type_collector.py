# Copyright 2021 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import argparse
import sys

from colcon_core.argument_parser.type_collector import SuppressTypeConversions
from colcon_core.argument_parser.type_collector import TypeCollectorDecorator
import pytest


class _RaisingArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        raise sys.exc_info()[1]


def test_type_collector_decorator():
    parser = argparse.ArgumentParser()
    decorator = TypeCollectorDecorator(parser)
    decorator.add_argument('positional')
    assert decorator.get_types() == {}

    decorator.add_argument('--option', type=bool)
    assert decorator.get_types() == {bool: bool}


def test_suppress_type_conversions():
    parser = _RaisingArgumentParser()
    decorator = TypeCollectorDecorator(parser)
    decorator.add_argument('-f', type=float)
    decorator.add_argument('-i', type=int)
    decorator.register('action', 'not_implemented', argparse.Action)
    decorator.register('type', 'hex', float.fromhex)
    decorator.add_argument('-x', type='hex', default=None)

    args = parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])
    assert 3.14 == args.f
    assert 1 == args.i
    assert 0x42 == args.x

    with SuppressTypeConversions((decorator,)):
        parser.parse_args(['-f', 'bar', '-i', '1', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(['-f', 'bar', '-i', '1', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        with SuppressTypeConversions((decorator,), {float}):
            parser.parse_args(['-f', 'bar', '-i', '1', '-x', '0x42'])

    with SuppressTypeConversions((decorator,)):
        parser.parse_args(['-f', '3.14', '-i', 'bar', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(['-f', '3.14', '-i', 'bar', '-x', '0x42'])
    with pytest.raises(argparse.ArgumentError):
        with SuppressTypeConversions((decorator,), {int}):
            parser.parse_args(['-f', '3.14', '-i', 'bar', '-x', '0x42'])

    with SuppressTypeConversions((decorator,)):
        parser.parse_args(['-f', '3.14', '-i', '1', '-x', 'foo'])
    with pytest.raises(argparse.ArgumentError):
        parser.parse_args(['-f', '3.14', '-i', '1', '-x', 'foo'])
    with pytest.raises(argparse.ArgumentError):
        with SuppressTypeConversions((decorator,), {'hex'}):
            parser.parse_args(['-f', '3.14', '-i', '1', '-x', 'foo'])

    args = parser.parse_args(['-f', '3.14', '-i', '1', '-x', '0x42'])
    assert 3.14 == args.f
    assert 1 == args.i
    assert 0x42 == args.x


def test_suppress_not_decorated():
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
