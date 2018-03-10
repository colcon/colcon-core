# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobStarted
from colcon_core.event_handler.console_start_end \
    import ConsoleStartEndEventHandler
from colcon_core.subprocess import SIGINT_RESULT
from mock import patch


def test_console_start_end():
    extension = ConsoleStartEndEventHandler()

    with patch('sys.stdout') as stdout:
        with patch('sys.stderr') as stderr:
            event = JobStarted('idA')
            extension((event, None))
            assert stdout.write.call_count == 2
            stdout.write.reset_mock()

            # success
            event = JobEnded('idA', 0)
            extension((event, None))
            assert stdout.write.call_count == 2
            stdout.write.reset_mock()

            # aborted
            event = JobEnded('idA', SIGINT_RESULT)
            extension((event, None))
            assert stdout.write.call_count == 2
            stdout.write.reset_mock()

            # failure
            event = JobEnded('idA', 1)
            extension((event, None))
            assert stderr.write.call_count == 2
            stderr.write.reset_mock()

            extension(('unknown', None))
            assert stdout.write.call_count == 0
            assert stderr.write.call_count == 0
