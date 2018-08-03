# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import argparse

from colcon_core.event_handler import add_event_handler_arguments
from colcon_core.event_handler import apply_event_handler_arguments
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.event_handler import format_duration
from colcon_core.event_handler import get_event_handler_extensions
from mock import Mock
import pytest

from .entry_point_context import EntryPointContext


class Extension1(EventHandlerExtensionPoint):
    """Some doc block."""

    def __init__(self):
        super().__init__()
        self.enabled = False


class Extension2(EventHandlerExtensionPoint):
    """Other doc block."""

    PRIORITY = 90


class Extension3(EventHandlerExtensionPoint):
    pass


def test_extension_interface():
    extension = Extension1()
    with pytest.raises(NotImplementedError):
        extension(None)


def test_get_shell_extensions():
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        extensions = get_event_handler_extensions(context=None)
    assert list(extensions.keys()) == [
        'extension1', 'extension3', 'extension2']


def test_add_event_handler_arguments():
    parser = argparse.ArgumentParser()
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        add_event_handler_arguments(parser)
    text = parser.format_help()
    assert 'extension1- extension2+ extension3+' in text
    assert '* extension1:' in text
    assert 'Some doc block' in text
    assert '* extension2:' in text
    assert 'Other doc block' in text


def test_apply_event_handler_arguments():
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3,
    ):
        extensions = get_event_handler_extensions(context=None)
    assert extensions['extension1'].enabled is False
    assert extensions['extension2'].enabled is True
    assert extensions['extension3'].enabled is True

    extensions['extension3'].enabled = None
    args = Mock()
    args.event_handlers = ['extension1+', 'extension2-']
    apply_event_handler_arguments(extensions, args)
    assert extensions['extension1'].enabled is True
    assert extensions['extension2'].enabled is False
    assert extensions['extension3'].enabled is None


def test_format_duration():
    # seconds below 10 with two decimal points
    assert format_duration(0) == '0.00s'
    assert format_duration(0.001) == '0.00s'
    assert format_duration(0.004999) == '0.00s'
    assert format_duration(0.005) == '0.01s'
    assert format_duration(9.99) == '9.99s'
    assert format_duration(9.994999) == '9.99s'
    assert format_duration(9.995) == '9.99s'  # floating point imprecision
    # seconds between 10 and 60 with one decimal points
    assert format_duration(9.995001) == '10.0s'
    assert format_duration(10) == '10.0s'
    assert format_duration(59.94) == '59.9s'
    # seconds above one minute with no decimal points
    assert format_duration(59.95) == '1min 0s'
    assert format_duration(83.45) == '1min 23s'
    assert format_duration(119.49) == '1min 59s'
    assert format_duration(119.5) == '2min 0s'
    assert format_duration(3599.4) == '59min 59s'
    # seconds above one hour with no decimal points
    assert format_duration(3599.5) == '1h 0min 0s'
    assert format_duration(5025.123) == '1h 23min 45s'
    assert format_duration(3599999) == '999h 59min 59s'
    # zero fixed decimal point
    assert format_duration(1.5, fixed_decimal_points=0) == '2s'
    assert format_duration(12.345, fixed_decimal_points=0) == '12s'
    # one fixed decimal points
    assert format_duration(1.5, fixed_decimal_points=1) == '1.5s'
    assert format_duration(12.345, fixed_decimal_points=1) == '12.3s'
    assert format_duration(34.5, fixed_decimal_points=1) == '34.5s'
    assert format_duration(3599.4, fixed_decimal_points=1) == '59min 59.4s'
    assert format_duration(4984.5, fixed_decimal_points=1) == '1h 23min 4.5s'
    # raise for negative parameter
    with pytest.raises(ValueError):
        format_duration(-1.0)
