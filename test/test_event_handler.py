# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import argparse

from colcon_core.event_handler import add_event_handler_arguments
from colcon_core.event_handler import apply_event_handler_arguments
from colcon_core.event_handler import EventHandlerExtensionPoint
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
