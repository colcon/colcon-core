# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio
from collections import OrderedDict
import os
import signal
import sys
from threading import Thread
import time

from colcon_core.executor import Job
from colcon_core.executor import OnError
from colcon_core.executor.sequential import SequentialExecutor
import pytest

ran_jobs = []


class Job1(Job):

    def __init__(self):
        super().__init__(
            identifier='job1', dependencies=set(), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        global ran_jobs
        ran_jobs.append(self.identifier)


class Job2(Job):

    def __init__(self):
        super().__init__(
            identifier='job2', dependencies=set(), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        return 2


class Job3(Job):

    def __init__(self):
        super().__init__(
            identifier='job3', dependencies=set(), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        raise RuntimeError('custom exception')


class Job4(Job):

    def __init__(self):
        super().__init__(
            identifier='job4', dependencies=set(), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        global ran_jobs
        ran_jobs.append(self.identifier)


class Job5(Job):

    def __init__(self):
        super().__init__(
            identifier='job5', dependencies=set(), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        return 5


class Job6(Job):

    def __init__(self):
        super().__init__(
            identifier='job6', dependencies=('job2', ), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        global ran_jobs
        ran_jobs.append(self.identifier)


class Job7(Job):

    def __init__(self):
        super().__init__(
            identifier='job7', dependencies=('job1', ), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        global ran_jobs
        ran_jobs.append(self.identifier)


def test_sequential():
    global ran_jobs
    extension = SequentialExecutor()

    args = None
    jobs = OrderedDict()
    jobs['one'] = Job1()

    # success
    rc = extension.execute(args, jobs)
    assert rc == 0
    assert ran_jobs == ['job1']
    ran_jobs.clear()

    # return error code
    jobs['two'] = Job2()
    jobs['four'] = Job4()
    rc = extension.execute(args, jobs)
    assert rc == 2
    assert ran_jobs == ['job1']
    ran_jobs.clear()

    rc = extension.execute(args, jobs, on_error=OnError.skip_pending)
    assert rc == 2
    assert ran_jobs == ['job1']
    ran_jobs.clear()

    # continue after error, keeping first error code
    jobs['five'] = Job5()
    rc = extension.execute(args, jobs, on_error=OnError.continue_)
    assert rc == 2
    assert ran_jobs == ['job1', 'job4']
    ran_jobs.clear()

    # continue but skip downstream
    jobs['six'] = Job6()
    jobs['seven'] = Job7()
    rc = extension.execute(args, jobs, on_error=OnError.skip_downstream)
    assert rc == 2
    assert ran_jobs == ['job1', 'job4', 'job7']
    ran_jobs.clear()

    # exception
    jobs['two'] = Job3()
    rc = extension.execute(args, jobs)
    assert rc == 1
    assert ran_jobs == ['job1']
    ran_jobs.clear()


class Job8(Job):

    def __init__(self):
        super().__init__(
            identifier='job8', dependencies=set(), task=None,
            task_context=None)

    async def __call__(self, *args, **kwargs):
        global ran_jobs
        await asyncio.sleep(3)
        ran_jobs.append(self.identifier)


@pytest.fixture
def restore_sigint_handler():
    handler = signal.getsignal(signal.SIGINT)
    yield
    signal.signal(signal.SIGINT, handler)


def test_sequential_keyboard_interrupt(restore_sigint_handler):
    global ran_jobs

    if sys.platform == 'win32':
        pytest.skip(
            'Skipping keyboard interrupt test since the signal will cause '
            'pytest to return failure even if no tests fail.')

    extension = SequentialExecutor()

    args = None
    jobs = OrderedDict()
    jobs['one'] = Job1()
    jobs['aborted'] = Job8()
    jobs['four'] = Job4()

    def delayed_sigint():
        time.sleep(0.1)
        # Note: a real Ctrl-C would signal the whole process group
        os.kill(
            os.getpid(),
            signal.SIGINT if sys.platform != 'win32' else signal.CTRL_C_EVENT)
        if sys.platform == 'win32':
            os.kill(os.getpid(), signal.CTRL_C_EVENT)

    thread = Thread(target=delayed_sigint)
    thread.start()
    try:
        rc = extension.execute(args, jobs)
    finally:
        thread.join()

    assert rc == signal.SIGINT
    ran_jobs.clear()
