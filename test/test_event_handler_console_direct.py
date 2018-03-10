# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.event.output import StderrLine
from colcon_core.event.output import StdoutLine
from colcon_core.event_handler.console_direct import ConsoleDirectEventHandler
from mock import patch


def test_console_direct():
    extension = ConsoleDirectEventHandler()

    with patch('sys.stdout') as stdout:
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
