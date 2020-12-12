# Copyright 2020 Scott K Logan
# Licensed under the Apache License, Version 2.0

import argparse

from colcon_core.argument_parser.type_collector import SuppressTypeConversions
from colcon_core.argument_parser.type_collector import TypeCollectorDecorator
import pytest


def test_type_collector_decorator():
    parser = argparse.ArgumentParser()
    decorator = TypeCollectorDecorator(parser)
    decorator.add_argument('positional')
    assert decorator.get_types() == {}

    decorator.add_argument('--option', type=bool)
    assert decorator.get_types() == {bool: bool}


def test_suppress_type_conversions():
    parser = argparse.ArgumentParser(exit_on_error=False)
    decorator = TypeCollectorDecorator(parser)
    decorator.add_argument('-f', type=float)
    decorator.add_argument('-i', type=int)
    decorator.register('type', 'hex', float.fromhex)
    decorator.add_argument('-x', type='hex', default=None)

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
