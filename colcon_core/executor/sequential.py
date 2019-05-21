# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio
import logging
import signal
import sys
import traceback

from colcon_core.executor import ExecutorExtensionPoint
from colcon_core.executor import OnError
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_core.subprocess import new_event_loop
from colcon_core.subprocess import SIGINT_RESULT

logger = colcon_logger.getChild(__name__)


class SequentialExecutor(ExecutorExtensionPoint):
    """
    Process one package at a time.

    The sequence follows the topological ordering.
    """

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            ExecutorExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def execute(self, args, jobs, *, on_error=OnError.interrupt):  # noqa: D102
        # avoid debug message from asyncio when colcon uses debug log level
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.INFO)

        rc = 0
        loop = new_event_loop()
        asyncio.set_event_loop(loop)
        jobs = jobs.copy()
        try:
            while jobs:
                name, job = jobs.popitem(last=False)
                coro = job()
                future = asyncio.ensure_future(coro, loop=loop)
                try:
                    logger.debug(
                        "run_until_complete '{name}'".format_map(locals()))
                    loop.run_until_complete(future)
                except KeyboardInterrupt:
                    logger.debug(
                        "run_until_complete '{name}' was interrupted"
                        .format_map(locals()))
                    # override job rc with special SIGINT value
                    job.returncode = SIGINT_RESULT
                    # ignore further SIGINTs
                    signal.signal(signal.SIGINT, signal.SIG_IGN)
                    # wait for job which has also received a SIGINT
                    if not future.done():
                        logger.debug(
                            "run_until_complete '{name}' again"
                            .format_map(locals()))
                        loop.run_until_complete(future)
                        assert future.done()
                    # read potential exception to avoid asyncio error
                    _ = future.exception()  # noqa: F841
                    logger.debug(
                        "run_until_complete '{name}' finished"
                        .format_map(locals()))
                    return signal.SIGINT
                except Exception as e:  # noqa: F841
                    exc = traceback.format_exc()
                    logger.error(
                        "Exception in job execution '{name}': {e}\n{exc}"
                        .format_map(locals()))
                    return 1
                result = future.result()
                logger.debug(
                    "run_until_complete '{name}' finished with '{result}'"
                    .format_map(locals()))
                if result:
                    if not rc:
                        rc = result
                    if on_error in (OnError.interrupt, OnError.skip_pending):
                        # skip pending jobs
                        return rc
                    if on_error == OnError.skip_downstream:
                        # skip downstream jobs of failed one
                        for pending_name, pending_job in list(jobs.items()):
                            if job.identifier in pending_job.dependencies:
                                del jobs[pending_name]

        finally:
            try:
                # new in Python 3.7
                all_tasks = asyncio.all_tasks
            except AttributeError:
                all_tasks = asyncio.Task.all_tasks
            for task in all_tasks(loop):
                if not task.done():
                    logger.error("Task '{task}' not done".format_map(locals()))
            # HACK on Windows closing the event loop seems to hang after Ctrl-C
            # even though no futures are pending
            if sys.platform != 'win32':
                logger.debug('closing loop')
                loop.close()
                logger.debug('loop closed')
        return rc
