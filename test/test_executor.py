# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from argparse import ArgumentParser
from concurrent.futures import CancelledError

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobQueued
from colcon_core.event.job import JobSkipped
from colcon_core.event.job import JobStarted
from colcon_core.event.output import StderrLine
from colcon_core.executor import add_executor_arguments
from colcon_core.executor import DEFAULT_EXECUTOR_ENVIRONMENT_VARIABLE
from colcon_core.executor import execute_jobs
from colcon_core.executor import ExecutorExtensionPoint
from colcon_core.executor import get_executor_extensions
from colcon_core.executor import Job
from colcon_core.subprocess import SIGINT_RESULT
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext
from .environment_context import EnvironmentContext
from .run_until_complete import run_until_complete


class Task:

    def __init__(self):
        self.return_value = None

    def set_context(self, *, context):
        pass

    async def __call__(self, *args, **kwargs):
        if isinstance(self.return_value, Exception):
            raise self.return_value
        return self.return_value


def test_job():
    task = Task()
    task_context = Mock()
    task_context.dependencies = Mock()
    task_context.pkg = Mock()
    task_context.pkg.name = 'name'
    job = Job(
        identifier='id', dependencies=set(), task=task,
        task_context=task_context)
    assert str(job) == 'id'

    events = []
    event_queue = Mock()
    event_queue.put = lambda event: events.append(event)
    job.set_event_queue(event_queue)
    assert len(events) == 1
    assert isinstance(events[-1][0], JobQueued)
    assert events[-1][0].identifier == 'name'
    assert events[-1][0].dependencies == task_context.dependencies
    assert events[-1][1] == job

    # successful task
    rc = run_until_complete(job())
    assert rc is 0
    assert len(events) == 3
    assert isinstance(events[-2][0], JobStarted)
    assert events[-2][0].identifier == 'name'
    assert events[-2][1] == job
    assert isinstance(events[-1][0], JobEnded)
    assert events[-1][0].identifier == 'name'
    assert events[-1][0].rc is 0
    assert events[-1][1] == job

    # canceled task
    job.returncode = None
    task.return_value = CancelledError()
    rc = run_until_complete(job())
    assert rc is SIGINT_RESULT
    assert len(events) == 5
    assert isinstance(events[-2][0], JobStarted)
    assert events[-2][0].identifier == 'name'
    assert events[-2][1] == job
    assert isinstance(events[-1][0], JobEnded)
    assert events[-1][0].identifier == 'name'
    assert events[-1][0].rc is SIGINT_RESULT
    assert events[-1][1] == job

    # task raising exception
    job.returncode = None
    task.return_value = RuntimeError('custom exception')
    with pytest.raises(RuntimeError):
        run_until_complete(job())
    assert len(events) == 8
    assert isinstance(events[-3][0], JobStarted)
    assert events[-3][0].identifier == 'name'
    assert events[-3][1] == job
    assert isinstance(events[-2][0], StderrLine)
    assert events[-2][0].line.endswith(b'\nRuntimeError: custom exception\n')
    assert events[-2][1] == job
    assert isinstance(events[-1][0], JobEnded)
    assert events[-1][0].identifier == 'name'
    assert events[-1][0].rc is 1
    assert events[-1][1] == job

    # override task return code
    job.returncode = 2
    task.return_value = 0
    rc = run_until_complete(job())
    assert rc is 2
    assert len(events) == 10
    assert isinstance(events[-2][0], JobStarted)
    assert events[-2][0].identifier == 'name'
    assert events[-2][1] == job
    assert isinstance(events[-1][0], JobEnded)
    assert events[-1][0].identifier == 'name'
    assert events[-1][0].rc is 2
    assert events[-1][1] == job


def test_interface():
    interface = ExecutorExtensionPoint()
    interface._flush()
    event_controller = Mock()
    interface.set_event_controller(event_controller)
    interface._flush()
    assert event_controller.flush.call_count == 1


class Extension1(ExecutorExtensionPoint):
    """Class documentation."""


class Extension2(ExecutorExtensionPoint):
    PRIORITY = 110


class Extension3(ExecutorExtensionPoint):
    pass


def test_add_executor_arguments():
    parser = ArgumentParser()
    # extensions with the same priority
    with EntryPointContext(
        extension1=Extension1, extension2=Extension2, extension3=Extension3
    ):
        with pytest.raises(AssertionError) as e:
            add_executor_arguments(parser)
        assert 'Executor extensions must have unique priorities' in str(e)

    # no extensions
    with EntryPointContext():
        with pytest.raises(AssertionError) as e:
            add_executor_arguments(parser)
        assert 'No executor extensions found' in str(e)

    # choose executor by environment variable
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_executor_extensions()
        extensions[110]['extension2'].add_arguments = Mock(
            side_effect=RuntimeError('custom exception'))
        extensions[100]['extension1'].add_arguments = Mock(return_value=None)
        env = {DEFAULT_EXECUTOR_ENVIRONMENT_VARIABLE.name: 'extension1'}
        with EnvironmentContext(**env):
            with patch('colcon_core.executor.logger.error') as error:
                add_executor_arguments(parser)
    assert extensions[100]['extension1'].add_arguments.call_count == 1
    # the raised exception is catched and results in an error message
    assert error.call_count == 1
    assert len(error.call_args[0]) == 1
    assert error.call_args[0][0].startswith(
        "Exception in executor extension 'extension2': custom exception\n")
    args = parser.parse_args([])
    assert args.executor == 'extension1'

    # choose default executor
    parser = ArgumentParser()
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        add_executor_arguments(parser)
    args = parser.parse_args([])
    assert args.executor == 'extension2'


def test_execute_jobs():
    context = Mock()
    context.args = Mock()
    context.args.event_handlers = None
    task_context = Mock()
    task_context.pkg = Mock()
    task_context.pkg.name = 'name'
    jobs = {
        'one': Job(
            identifier='id', dependencies=set(), task=None,
            task_context=task_context)}

    event_reactor = Mock()
    with patch(
        'colcon_core.executor.create_event_reactor', return_value=event_reactor
    ):
        with EntryPointContext(extension1=Extension1, extension2=Extension2):
            # no extension selected
            with pytest.raises(AssertionError):
                execute_jobs(context, jobs)

            # execute method not implemented and sending skipped job event
            context.args.executor = 'extension2'
            with patch('colcon_core.executor.logger.error') as error:
                rc = execute_jobs(context, jobs)
            assert rc is 1
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in executor extension 'extension2': \n")
            assert event_reactor.get_queue().put.call_count == 2
            assert isinstance(
                event_reactor.get_queue().put.call_args_list[0][0][0][0],
                JobQueued)
            assert isinstance(
                event_reactor.get_queue().put.call_args_list[1][0][0][0],
                JobSkipped)

            # successful execution
            event_reactor.get_queue().put.reset_mock()
            jobs['one'].returncode = 0
            extensions = get_executor_extensions()
            extensions[110]['extension2'].execute = Mock(return_value=0)
            rc = execute_jobs(context, jobs)
            assert rc is 0
            assert event_reactor.get_queue().put.call_count == 1
            assert isinstance(
                event_reactor.get_queue().put.call_args[0][0][0], JobQueued)
