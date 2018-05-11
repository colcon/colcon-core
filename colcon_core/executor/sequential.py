# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio
import logging
import signal
import traceback

from colcon_core.executor import ExecutorExtensionPoint
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

    def execute(self, args, jobs, *, abort_on_error=True):  # noqa: D102
        # avoid debug message from asyncio when colcon uses debug log level
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.INFO)

        rc = 0
        loop = new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for name, job in jobs.items():
                coro = job()
                future = asyncio.ensure_future(coro, loop=loop)
                try:
                    logger.debug(
                        "run_until_complete '{name}'".format_map(locals()))
                    loop.run_until_complete(future)
                except KeyboardInterrupt:
                    logger.debug(
                        "run_until_complete '{name}' was interrupted, "
                        'run_until_complete again'.format_map(locals()))
                    # override job rc with special SIGINT value
                    job.returncode = SIGINT_RESULT
                    # ignore further SIGINTs
                    signal.signal(signal.SIGINT, signal.SIG_IGN)
                    # wait for job which has also received a SIGINT
                    loop.run_until_complete(future)
                    logger.debug(
                        "run_until_complete '{name}' finished"
                        .format_map(locals()))
                    raise
                except Exception as e:
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
                    if abort_on_error:
                        return rc
        finally:
            loop.close()
        return rc
