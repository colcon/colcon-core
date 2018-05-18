# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio
from collections import OrderedDict
import os
import signal
import sys
from threading import Thread
import time

from colcon_core.executor.sequential import SequentialExecutor
import pytest

ran_jobs = []


async def job1():
    global ran_jobs
    ran_jobs.append('job1')


async def job2():
    return 2


async def job3():
    raise RuntimeError('custom exception')


async def job4():
    global ran_jobs
    ran_jobs.append('job4')


async def job5():
    return 5


def test_sequential():
    global ran_jobs
    extension = SequentialExecutor()

    args = None
    jobs = OrderedDict()
    jobs['one'] = job1

    # success
    rc = extension.execute(args, jobs)
    assert rc == 0
    assert ran_jobs == ['job1']
    ran_jobs.clear()

    # return error code
    jobs['two'] = job2
    jobs['four'] = job4
    rc = extension.execute(args, jobs)
    assert rc == 2
    assert ran_jobs == ['job1']
    ran_jobs.clear()

    # continue after error, keeping first error code
    jobs['five'] = job5
    rc = extension.execute(args, jobs, abort_on_error=False)
    assert rc == 2
    assert ran_jobs == ['job1', 'job4']
    ran_jobs.clear()

    # exception
    jobs['two'] = job3
    rc = extension.execute(args, jobs)
    assert rc == 1
    assert ran_jobs == ['job1']
    ran_jobs.clear()


async def job6():
    global ran_jobs
    await asyncio.sleep(1)
    ran_jobs.append('job6')


def test_sequential_keyboard_interrupt():
    global ran_jobs

    if 'APPVEYOR' in os.environ:
        pytest.skip(
            'Skipping keyboard interrupt test since otherwise the prompt '
            "'Terminate batch job' blocks the build on AppVeyor")

    extension = SequentialExecutor()

    args = None
    jobs = OrderedDict()
    jobs['one'] = job1
    jobs['aborted'] = job6
    jobs['four'] = job4

    def delayed_sigint():
        time.sleep(0.1)
        os.kill(
            os.getpid(),
            signal.SIGINT if sys.platform != 'win32' else signal.CTRL_C_EVENT)
        if sys.platform == 'win32':
            os.kill(signal.CTRL_C_EVENT)

    thread = Thread(target=delayed_sigint)
    try:
        thread.start()
        rc = extension.execute(args, jobs)
        assert rc == signal.SIGINT
    finally:
        thread.join()
