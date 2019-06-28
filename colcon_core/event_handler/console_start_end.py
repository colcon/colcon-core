# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import sys
import time

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobStarted
from colcon_core.event.test import TestFailure
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.event_handler import format_duration
from colcon_core.plugin_system import satisfies_version
from colcon_core.subprocess import SIGINT_RESULT

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    FIN = '\x1b[1;30m'
    FINBR = '\033[32m'
    START = '\x1b[1;37m'
    STARTBR = '\033[92m'
    TIME = '\x1b[1;33m'
    PKG_NAME = '\033[96m'




class ConsoleStartEndEventHandler(EventHandlerExtensionPoint):
    """
    Output task name on start/end.

    The extension handles events of the following types:
    - :py:class:`colcon_core.event.job.JobStarted`
    - :py:class:`colcon_core.event.job.JobEnded`
    - :py:class:`colcon_core.event.test.TestFailure`
    """

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self._start_times = {}
        self._with_test_failures = set()

    def __call__(self, event):  # noqa: D102
        data = event[0]

        if isinstance(data, JobStarted):
            msg_template=bcolors.START + 'Starting ' + bcolors.STARTBR+ '>>>' + bcolors.PKG_NAME + ' {data.identifier}' + bcolors.ENDC
            print(msg_template.format_map(locals()),
                flush=True)
            self._start_times[data.identifier] = time.time()

        elif isinstance(data, TestFailure):
            job = event[1]
            self._with_test_failures.add(job)

        elif isinstance(data, JobEnded):
            if not data.rc:
                duration = time.time() - self._start_times[data.identifier]
                duration_string = format_duration(duration)
                msg_template = bcolors.FIN + 'Finished '+ bcolors.FINBR + '<<<'+ bcolors.PKG_NAME + ' {data.identifier}' + bcolors.ENDC +' ['+bcolors.TIME+'{duration_string}'+bcolors.ENDC+']'
                msg =  msg_template.format_map(locals())
                job = event[1]
                if job in self._with_test_failures:
                    msg += '\t[ with test failures ]'
                writable = sys.stdout

            elif data.rc == SIGINT_RESULT:
                msg_template = bcolors.WARNING + 'Aborted  ' + '<<<'+ bcolors.PKG_NAME + ' {data.identifier}' + bcolors.ENDC
                msg = msg_template.format_map(locals())
                writable = sys.stdout
            else:
                msg_template = bcolors.FAIL + 'Failed   ' + '<<<'+ bcolors.PKG_NAME + ' {data.identifier}' + bcolors.ENDC +' ['+bcolors.FAIL+'Exited with code {data.rc}'+bcolors.ENDC+']'
                msg = msg_template.format_map(locals())
                writable = sys.stderr

            print(msg, file=writable, flush=True)
