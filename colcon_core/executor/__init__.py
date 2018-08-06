# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from concurrent.futures import CancelledError
import os
import traceback

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobQueued
from colcon_core.event.job import JobSkipped
from colcon_core.event.job import JobStarted
from colcon_core.event.output import StderrLine
from colcon_core.event_reactor import create_event_reactor
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import get_first_line_doc
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_grouped_by_priority
from colcon_core.subprocess import SIGINT_RESULT

logger = colcon_logger.getChild(__name__)

"""Environment variable to override the default executor"""
DEFAULT_EXECUTOR_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_DEFAULT_EXECUTOR', 'Select the default executor extension')


class Job:
    """A job describes a unit of work."""

    def __init__(self, *, identifier, dependencies, task, task_context):
        """
        Constructor.

        :param str identifier: The job identifier
        :param set dependencies: The identifiers of other jobs which this job
          depends on
        :param task: The task extension
        :param task_context: The task context
        """
        self._event_queue = None
        self.identifier = identifier
        self.dependencies = dependencies
        self.task = task
        self.returncode = None
        self.task_context = task_context

    def set_event_queue(self, event_queue):
        """
        Set the event queue.

        Using the event queue the job can post events.
        A :class:`JobQueued` event with the package name from the task context
        is posted to the event queue.

        :param event_queue: The event queue
        """
        self._event_queue = event_queue

        self._put_event_into_queue(JobQueued(
            self.task_context.pkg.name, self.task_context.dependencies))

    async def __call__(self, *args, **kwargs):
        """
        Perform the unit of work.

        The overview of the process:
        * Put a :class:`JobStarted` event into the queue
        * Pass the task context to the task
        * Invoke the task
        * In case the task is canceled return a :attribute:`SIGINT_RESULT`
          code
        * In case of an exception within the task put a :class:`StderrLine`
          event into the queue and re-raise the exception
        * Put a :class:`JobEnded` event into the queue

        :returns: The return code of the invoked task
        :raises Exception: Any exception the invoked task raises
        """
        self._put_event_into_queue(JobStarted(self.task_context.pkg.name))

        # replace function to use this job as the event context
        self.task_context.put_event_into_queue = self._put_event_into_queue
        self.task.set_context(context=self.task_context)

        rc = 0
        try:
            rc = await self.task(*args, **kwargs)
        except CancelledError:
            rc = SIGINT_RESULT
        except Exception:
            rc = 1
            self._put_event_into_queue(
                StderrLine(traceback.format_exc().encode()))
            raise
        finally:
            if self.returncode is None:
                self.returncode = rc or 0
            self._put_event_into_queue(
                JobEnded(self.task_context.pkg.name, self.returncode))
        return self.returncode

    def _put_event_into_queue(self, event):
        self._event_queue.put((event, self))

    def __str__(self):
        """Use the identifier as the string representation of a job."""
        return self.identifier


class ExecutorExtensionPoint:
    """
    The interface for executor extensions.

    An executor extension runs a set of jobs.

    For each instance the attribute `EXECUTOR_NAME` is being set to the
    basename of the entry point registering the extension.
    """

    """The version of the executor extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of executor extensions."""
    PRIORITY = 100

    def __init__(self):  # noqa: D107
        super().__init__()
        self._event_controller = None

    def add_arguments(self, *, parser):
        """
        Add command line arguments specific to the executor.

        The method is intended to be overridden in a subclass.

        :param parser: The argument parser
        """
        pass

    def set_event_controller(self, event_controller):
        """
        Set the event controller.

        Using the event controller the executor can force a flush of all
        events.
        """
        self._event_controller = event_controller

    def execute(self, args, jobs, *, abort_on_error=True):
        """
        Execute the passed jobs.

        This method must be overridden in a subclass.

        :param args: The parsed command line arguments
        :param jobs: The jobs
        :param abort_on_error: The flag if pending jobs should be aborted in
          case of any errors or individual jobs failing
        """
        raise NotImplementedError()

    def _flush(self):
        if self._event_controller is None:
            return
        self._event_controller.flush()


def get_executor_extensions():
    """
    Get the available executor extensions.

    The extensions are grouped by their priority and each group is ordered by
    the entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.EXECUTOR_NAME = name
    return order_extensions_grouped_by_priority(extensions)


def add_executor_arguments(parser):
    """
    Add the command line arguments for the executor extensions.

    :param parser: The argument parser
    """
    group = parser.add_argument_group(title='Executor arguments')
    extensions = get_executor_extensions()
    keys = []
    descriptions = ''
    for priority in extensions.keys():
        extensions_same_prio = extensions[priority]
        assert len(extensions_same_prio) == 1, \
            'Executor extensions must have unique priorities'
        for key, extension in extensions_same_prio.items():
            keys.append(key)
            desc = get_first_line_doc(extension)
            if not desc:
                # show extensions without a description
                # to mention the available options
                desc = '<no description>'
            # it requires a custom formatter to maintain the newline
            descriptions += '\n* {key}: {desc}'.format_map(locals())
    assert keys, 'No executor extensions found'

    default = os.environ.get(DEFAULT_EXECUTOR_ENVIRONMENT_VARIABLE.name)
    if default not in keys:
        default = keys[0]

    group.add_argument(
        '--executor', type=str, choices=keys, default=default,
        help='The executor to process all packages (default: {default})'
             '{descriptions}'.format_map(locals()))

    for priority in extensions.keys():
        extensions_same_prio = extensions[priority]
        for extension in extensions_same_prio.values():
            try:
                retval = extension.add_arguments(parser=group)
                assert retval is None, 'add_arguments() should return None'
            except Exception as e:
                # catch exceptions raised in executor extension
                exc = traceback.format_exc()
                logger.error(
                    'Exception in executor extension '
                    "'{extension.EXECUTOR_NAME}': {e}\n{exc}"
                    .format_map(locals()))
                # skip failing extension, continue with next one


def execute_jobs(context, jobs, *, abort_on_error=True):
    """
    Execute jobs.

    The overview of the process:
    * One executor extension is being chosen based on the command line
      arguments.
    * Create an event controller.
    * Pass the event controller to the executor extension.
    * Pass the event queue to all jobs.
    * Start the event controller.
    * Invoke the executor extension to execute the jobs.
    * Join the event controller.

    :param jobs: The ordered dictionary of jobs
    :param abort_on_error: The flag if pending jobs should be aborted in case
      of individual jobs failing
    :returns: The return code
    """
    executor = select_executor_extension(context.args)
    assert executor

    # create event reactor with handlers specified by the args
    event_controller = create_event_reactor(context)
    executor.set_event_controller(event_controller)

    # pass queue to jobs to publish events
    for job in jobs.values():
        job.set_event_queue(event_controller.get_queue())

    logger.info("Executing jobs using '%s' executor", executor.EXECUTOR_NAME)
    event_controller.start()
    try:
        rc = executor.execute(
            context.args, jobs, abort_on_error=abort_on_error)
    except Exception as e:
        # catch exceptions raised in executor extension
        exc = traceback.format_exc()
        logger.error(
            "Exception in executor extension '{executor.EXECUTOR_NAME}': "
            '{e}\n{exc}'.format_map(locals()))
        rc = 1
    finally:
        # generate an event for every skipped job
        for job in jobs.values():
            if job.returncode is not None:
                continue
            event_controller.get_queue().put((JobSkipped(job.identifier), job))

        event_controller.join()
    return rc


def select_executor_extension(args):
    """
    Get the executor extension.

    :param args: The parsed command line arguments
    :returns: The executor extension
    """
    executor_extensions = get_executor_extensions()
    for priority in executor_extensions.keys():
        extensions_same_prio = executor_extensions[priority]
        for key, extension in extensions_same_prio.items():
            if key == args.executor:
                return extension
    # one executor should always be selected by the default value
    # in case their are no executor extensions available the add argument
    # function should have already failed
    assert False
