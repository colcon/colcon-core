# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from unittest.mock import patch

from colcon_core.event.output import StderrLine
from colcon_core.event.output import StdoutLine
from colcon_core.event_handler.console_direct import ConsoleDirectEventHandler
import pytest


def test_console_direct():
    with patch('sys.stdout') as stdout:
        extension = ConsoleDirectEventHandler()

        event = StdoutLine(b'bytes line')
        extension((event, None))
        assert stdout.buffer.write.call_count == 1
        event = StdoutLine('string line')
        extension((event, None))
        assert stdout.write.call_count == 1

        stdout.buffer.write.reset_mock()
        stdout.write.reset_mock()
        extension(('unknown', None))
        assert stdout.buffer.write.call_count == 0
        assert stdout.write.call_count == 0

    with patch('sys.stderr') as stderr:
        extension = ConsoleDirectEventHandler()

        event = StderrLine(b'bytes line')
        extension((event, None))
        assert stderr.buffer.write.call_count == 1
        event = StderrLine('string line')
        extension((event, None))
        assert stderr.write.call_count == 1

        stderr.buffer.write.reset_mock()
        stderr.write.reset_mock()
        extension(('unknown', None))
        assert stderr.buffer.write.call_count == 0
        assert stderr.write.call_count == 0

    with patch('sys.stdout') as stdout:
        stdout.buffer.write.side_effect = BrokenPipeError()
        stdout.write.side_effect = BrokenPipeError()

        extension = ConsoleDirectEventHandler()

        event = StdoutLine(b'bytes line')
        with pytest.raises(BrokenPipeError):
            extension((event, None))
        assert stdout.buffer.write.call_count == 1
        event = StdoutLine(b'bytes line')
        extension((event, None))
        assert stdout.buffer.write.call_count == 1
        event = StdoutLine('string line')
        extension((event, None))
        assert stdout.write.call_count == 0
