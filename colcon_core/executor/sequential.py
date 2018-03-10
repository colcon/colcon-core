# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio
import logging
import signal

from colcon_core.executor import ExecutorExtensionPoint
from colcon_core.plugin_system import satisfies_version
from colcon_core.subprocess import new_event_loop
from colcon_core.subprocess import SIGINT_RESULT


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
        logger = logging.getLogger('asyncio')
        logger.setLevel(logging.INFO)

        rc = 0
        loop = new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for job in jobs.values():
                coro = job()
                future = asyncio.ensure_future(coro, loop=loop)
                try:
                    loop.run_until_complete(future)
                except KeyboardInterrupt:
                    # override job rc with special SIGINT value
                    job.returncode = SIGINT_RESULT
                    # ignore further SIGINTs
                    signal.signal(signal.SIGINT, signal.SIG_IGN)
                    # wait for job which has also received a SIGINT
                    loop.run_until_complete(future)
                    raise
                except Exception:
                    return 1
                if future.result():
                    if not rc:
                        rc = future.result()
                    if abort_on_error:
                        return rc
        finally:
            loop.close()
        return rc
