# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.event.command import Command
from colcon_core.event.command import CommandEnded
from colcon_core.event_handler.log_command import LogCommandEventHandler
from mock import patch


def test_console_direct():
    extension = LogCommandEventHandler()

    with patch('colcon_core.event_handler.log_command.logger.debug') as debug:
        event = Command(['executable'], cwd='/some/path')
        extension((event, None))
        assert debug.call_count == 1

        debug.reset_mock()
        event = CommandEnded(['executable'], cwd='/some/path', returncode=1)
        extension((event, None))
        assert debug.call_count == 1

        debug.reset_mock()
        extension(('unknown', None))
        assert debug.call_count == 0
