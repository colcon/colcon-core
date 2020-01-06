# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import asyncio
import sys

from colcon_core.subprocess import check_output
from colcon_core.subprocess import new_event_loop
from colcon_core.subprocess import run
import pytest

from .run_until_complete import run_until_complete


# TODO figure out how to avoid the stderr output
@pytest.mark.skip(
    reason='Results in stderr output due to a UnicodeDecodeError for the '
           'generated coverage files')
def test_check_output():
    coroutine = check_output(
        [sys.executable, '-c', r"print('line1\nline2')"], shell=True)
    output = run_until_complete(coroutine)
    assert output.decode().splitlines() == ['line1', 'line2']


# TODO figure out how to avoid the stderr output
@pytest.mark.skip(
    reason='Results in stderr output due to a UnicodeDecodeError for the '
           'generated coverage files')
def test_run():
    # without callbacks
    coroutine = run(
        [sys.executable, '-c', r"print('line1\nline2')"], None, None)
    completed_process = run_until_complete(coroutine)
    assert completed_process.returncode == 0

    # without callbacks, with pty
    coroutine = run(
        [sys.executable, '-c', r"print('line1\nline2')"], None, None,
        use_pty=True)
    completed_process = run_until_complete(coroutine)
    assert completed_process.returncode == 0

    # with callbacks
    stdout_lines = []
    stderr_lines = []

    def stdout_callback(line):
        nonlocal stdout_lines
        stdout_lines.append(line)

    def stderr_callback(line):
        nonlocal stderr_lines
        stderr_lines.append(line)

    coroutine = run(
        [sys.executable, '-c', r"print('line1\nline2')"],
        stdout_callback, stderr_callback)
    completed_process = run_until_complete(coroutine)
    assert completed_process.returncode == 0
    assert stdout_lines == [b'line1\n', b'line2\n']

    # with callbacks, with pty
    stdout_lines = []
    stderr_lines = []
    coroutine = run(
        [sys.executable, '-c', r"print('line1\nline2')"],
        stdout_callback, stderr_callback, use_pty=True)
    completed_process = run_until_complete(coroutine)
    assert completed_process.returncode == 0
    assert stdout_lines == [b'line1\n', b'line2\n']


# TODO figure out why no coverage is being generated
@pytest.mark.skip(
    reason='No coverage is being generated for this test')
def test_run_cancel():
    # with callbacks, canceled
    stdout_lines = []

    def stdout_callback(line):
        nonlocal stdout_lines
        stdout_lines.append(line)

    coroutine = run(
        [
            sys.executable, '-c',
            r"import time; time.sleep(1); print('line1\nline2')"],
        stdout_callback, None)
    loop = new_event_loop()
    asyncio.set_event_loop(loop)
    task = asyncio.Task(coroutine, loop=loop)
    assert task.cancel() is True
    try:
        with pytest.raises(asyncio.CancelledError):
            loop.run_until_complete(task)
    finally:
        loop.close()
