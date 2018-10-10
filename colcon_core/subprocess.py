# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

"""
Call a subprocess making the stdout and stderr output available via callbacks.

The stdout and stderr pipes are read concurrently using the asyncio event loop
to maintain the original order as closely as possible.
"""

import asyncio
from concurrent.futures import ALL_COMPLETED
from concurrent.futures import CancelledError
from functools import partial
import os
import platform
import shlex
import subprocess
import sys
from typing import Callable
from typing import Mapping
from typing import Sequence
from typing import TypeVar

from colcon_core.logging import colcon_logger

SIGINT_RESULT = 'SIGINT'

logger = colcon_logger.getChild(__name__)

UsePtyType = TypeVar('UsePtyType', None, bool)


def new_event_loop():
    """
    Create a new event loop.

    On Windows return a ProactorEventLoop.

    :returns: The created event loop
    """
    if sys.platform == 'win32':
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()


async def run(
    args: Sequence[str],
    stdout_callback: Callable[[bytes], None],
    stderr_callback: Callable[[bytes], None],
    *,
    cwd: str=None,
    env: Mapping[str, str]=None,
    shell: bool=False,
    use_pty: UsePtyType=None
) -> subprocess.CompletedProcess:
    """
    Run the command described by args.

    Invokes the callbacks for every line read from the subprocess pipes.

    :param args: args should be a sequence of program arguments
    :param stdout_callback: the callable is invoked for every line read from
      the stdout pipe of the process
    :param stderr_callback: the callable is invoked for every line read from
      the stderr pipe of the process
    :param cwd: the working directory for the subprocess
    :param env: a dictionary with environment variables
    :param shell: whether to use the shell as the program to execute
    :param use_pty: whether to use a pseudo terminal
    :returns: the result of the completed process
    """
    assert callable(stdout_callback) or stdout_callback is None
    assert callable(stderr_callback) or stderr_callback is None

    # if use_pty is neither True nor False choose based on isatty of stdout
    if use_pty is None:
        use_pty = sys.stdout.isatty()
    # the pty module is only supported on Windows
    if use_pty and platform.system() != 'Linux':
        use_pty = False

    rc, _, _ = await _async_check_call(
        args, stdout_callback, stderr_callback,
        cwd=cwd, env=env, shell=shell, use_pty=use_pty)
    return subprocess.CompletedProcess(args, rc)


async def check_output(
    args: Sequence[str],
    *,
    cwd: str=None,
    env: Mapping[str, str]=None,
    shell: bool=False
) -> subprocess.CompletedProcess:
    """
    Get the output of an invoked command.

    :param args: args should be a sequence of program arguments
    :param cwd: the working directory for the subprocess
    :param env: a dictionary with environment variables
    :param shell: whether to use the shell as the program to execute
    :returns: The `stdout` output of the command
    :rtype: str
    """
    rc, stdout_data, _ = await _async_check_call(
        args, subprocess.PIPE, None,
        cwd=cwd, env=env, shell=shell, use_pty=False)
    assert not rc, 'Expected {args} to pass'.format_map(locals())
    return stdout_data


async def _async_check_call(
    args, stdout_callback, stderr_callback, *,
    cwd=None, env=None, shell=False, use_pty=None
):
    """Coroutine running the command and invoking the callbacks."""
    # choose function to create subprocess
    if not shell:
        create_subprocess = asyncio.create_subprocess_exec
    else:
        args = [' '.join([escape_shell_argument(a) for a in args])]
        create_subprocess = asyncio.create_subprocess_shell

    # choose stdout and stderr arguments for the subprocess
    stdout = subprocess.PIPE if stdout_callback else subprocess.DEVNULL
    stderr = subprocess.PIPE if stderr_callback else subprocess.DEVNULL

    # open pseudo terminals
    if use_pty:
        # only import when requested since it is not available on all platforms
        import pty
        if stdout_callback:
            stdout_master, stdout = pty.openpty()
        if stderr_callback:
            stderr_master, stderr = pty.openpty()

    process = await create_subprocess(
        *args, cwd=cwd, env=env, stdout=stdout, stderr=stderr)

    # read pipes concurrently
    callbacks = []
    if use_pty:
        if callable(stdout_callback):
            stdout_master_fd = os.fdopen(stdout_master)
            callbacks.append(_fd2callback(stdout_master_fd, stdout_callback))
        if callable(stderr_callback):
            stderr_master_fd = os.fdopen(stderr_master)
            callbacks.append(_fd2callback(stderr_master_fd, stderr_callback))
    else:
        if callable(stdout_callback):
            callbacks.append(_pipe2callback(
                process.stdout, stdout_callback,
                process.stderr if callable(stderr_callback) else None))
        if callable(stderr_callback):
            callbacks.append(asyncio.ensure_future(_pipe2callback(
                process.stderr, stderr_callback,
                process.stdout if callable(stdout_callback) else None)))

    output = [None, None]
    if not stdout_callback and not stderr_callback:
        # asynchronously wait for the subprocess
        await process.wait()
    else:
        # asynchronously communicate with the subprocess
        callbacks.append(process.wait())
        if subprocess.PIPE in (stdout_callback, stderr_callback):
            callbacks.append(_communicate_and_close_fds(
                process,
                # collect output in case the process uses any pipes
                output,
                # pseudo terminals need to be closed explicitly
                stdout if use_pty else None, stderr if use_pty else None))
        else:
            callbacks.append(_wait_and_close_fds(
                process,
                # pseudo terminals need to be closed explicitly
                stdout if use_pty else None, stderr if use_pty else None))
        try:
            done, _ = await asyncio.wait(callbacks, return_when=ALL_COMPLETED)
        except CancelledError:
            # finish the communication with the subprocess
            done, _ = await asyncio.wait(callbacks, return_when=ALL_COMPLETED)
            raise
        finally:
            # read potential exceptions to avoid asyncio errors
            for task in done:
                _ = task.exception()  # noqa: F841

    return process.returncode, output[0], output[1]


def escape_shell_argument(arg):
    """
    Escape the shell arguments for an invocation through a shell.

    :param arg: A single command line argument
    :returns: The escaped command line argument
    :rtype: str
    """
    # some literals must not be quoted
    unquoted_values = [';', '|', '&&', '||']
    if arg in unquoted_values:
        return arg
    # some arguments don't need quoting
    if arg.startswith('`') and arg.endswith('`'):
        return arg
    if arg.startswith('$(') and arg.endswith(')'):
        return arg

    quoted = shlex.quote(arg)
    if sys.platform == 'win32':
        # Windows doesn't like paths with single quotes
        if len(quoted) > 1 and quoted.startswith("'") and quoted.endswith("'"):
            quoted = '"' + quoted[1:-1] + '"'

    return quoted


async def _fd2callback(stream, callback):
    """Coroutine reading from fd and invoking the callback for each line."""
    func = partial(_blocking_fd2callback, stream, callback)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, func)


def _blocking_fd2callback(stream, callback):
    """Read all lines from the stream invoke the callback for each line."""
    while True:
        try:
            line = stream.readline()
        except IOError:
            # this is how the fd signals the EOF
            break
        callback(line.encode())


async def _pipe2callback(stream, callback, other_stream=None):
    """Coroutine reading from pipe and invoking the callback for each line."""
    while True:
        line = await stream.readline()
        if not line:
            # this is how the pipe signals the EOF
            break
        callback(line)

    # HACK on Windows sometimes only one of the two streams gets closed
    # feeding an EOF explicitly ensures that the other coroutine finishes
    if sys.platform == 'win32' and other_stream:
        other_stream.feed_eof()


async def _wait_and_close_fds(process, stdout=None, stderr=None):
    """Wait for the process and ensure that all handles are closed."""
    try:
        await process.wait()
    finally:
        # always close handles even when a CancelledError is raised
        if stdout:
            os.close(stdout)
        if stderr:
            os.close(stderr)


async def _communicate_and_close_fds(
    process, output, stdout=None, stderr=None
):
    """Communicate with the process and close all handles."""
    stdout_data, stderr_data = await process.communicate()
    output[0] = stdout_data
    output[1] = stderr_data
    if stdout:
        os.close(stdout)
    if stderr:
        os.close(stderr)
