# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from colcon_core.event.command import Command
from colcon_core.event.job import JobProgress
from colcon_core.event.output import StderrLine
from colcon_core.event.output import StdoutLine
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.task import add_task_arguments
from colcon_core.task import create_file
from colcon_core.task import get_task_extension
from colcon_core.task import get_task_extensions
from colcon_core.task import install
from colcon_core.task import run
from colcon_core.task import TaskContext
from colcon_core.task import TaskExtensionPoint
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext
from .run_until_complete import run_until_complete


def test_context_interface():
    context = TaskContext(pkg=None, args=None, dependencies=None)
    with pytest.raises(NotImplementedError):
        context.put_event_into_queue(None)


class Extension(TaskExtensionPoint):
    TASK_NAME = 'do'

    async def do(self, *args, **kwargs):
        self.progress('progress')
        self.print('hello')
        self.print('hello', file=sys.stdout)
        self.print('world', file=sys.stderr)
        with pytest.raises(AssertionError):
            self.print('invalid file handle', file=False)
        return 1


def test_extension_interface():
    context = Mock()

    # capture events
    events = []

    def put_event_into_queue(event):
        nonlocal events
        events.append(event)

    context.put_event_into_queue = put_event_into_queue

    extension = Extension()
    extension.set_context(context=context)
    rc = run_until_complete(extension())
    assert rc == 1

    assert len(events) == 4
    assert isinstance(events[0], JobProgress)
    assert events[0].progress == 'progress'
    assert isinstance(events[1], StdoutLine)
    assert events[1].line == 'hello\n'
    assert isinstance(events[2], StdoutLine)
    assert events[2].line == 'hello\n'
    assert isinstance(events[3], StderrLine)
    assert events[3].line == 'world\n'


# TODO figure out how to avoid the stderr output
@pytest.mark.skip(
    reason='Results in stderr output due to a UnicodeDecodeError for the '
           'generated coverage files')
def test_run():
    context = Mock()
    events = []

    def put_event_into_queue(event):
        nonlocal events
        events.append(event)

    context.put_event_into_queue = put_event_into_queue
    cmd = [
        sys.executable, '-c',
        "import sys; print('hello'); print('world', file=sys.stderr)"]
    coroutine = run(context, cmd)
    completed_process = run_until_complete(coroutine)
    assert completed_process.returncode == 0
    assert len(events) == 3
    assert isinstance(events[0], Command)
    assert events[0].cmd == cmd
    assert isinstance(events[1], StdoutLine)
    assert events[1].line == b'hello\n'
    assert isinstance(events[2], StderrLine)
    assert events[2].line == b'world\n'


class Extension1(TaskExtensionPoint):

    def build(self, *args, **kwargs):
        pass  # pragma: no cover


class Extension2(TaskExtensionPoint):

    def build(self, *args, **kwargs):
        pass  # pragma: no cover


def instantiate_extensions_without_cache(
    group_name, *, exclude_names=None, unique_instance=False
):
    return instantiate_extensions(group_name)


def test_add_task_arguments():
    parser = Mock()
    task_name = 'colcon_core.task.build'
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        with patch(
            'colcon_core.task.instantiate_extensions',
            side_effect=instantiate_extensions_without_cache
        ):
            extensions = get_task_extensions(task_name)
            # one exception, one success
            extensions['extension1'].add_arguments = Mock(
                side_effect=RuntimeError('custom exception'))
            with patch('colcon_core.task.logger.error') as error:
                add_task_arguments(parser, task_name)
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in task extension 'build.extension1': custom "
                'exception\n')

            # invalid return value
            extensions['extension1'].add_arguments = Mock()
            extensions['extension2'].add_arguments = Mock(return_value=None)
            with patch('colcon_core.task.logger.error') as error:
                add_task_arguments(parser, task_name)
            assert error.call_count == 1
            assert len(error.call_args[0]) == 1
            assert error.call_args[0][0].startswith(
                "Exception in task extension 'build.extension1': "
                'add_arguments() should return None\n')
            assert extensions['extension2'].add_arguments.call_count == 1


def test_get_task_extension():
    task_name = 'colcon_core.task.build'
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        # request invalid extension
        extension = get_task_extension(task_name, 'package_type')
        assert extension is None

        # request valid extension
        extension = get_task_extension(task_name, 'extension2')
        assert isinstance(extension, Extension2)


def test_create_file():
    with TemporaryDirectory(prefix='test_colcon_') as base_path:
        args = Mock()
        args.install_base = base_path

        create_file(args, 'file.txt')
        path = Path(base_path) / 'file.txt'
        assert path.is_file()
        assert path.read_text() == ''

        create_file(args, 'path/file.txt', content='content')
        path = Path(base_path) / 'path' / 'file.txt'
        assert path.is_file()
        assert path.read_text() == 'content'


def test_install():
    with TemporaryDirectory(prefix='test_colcon_') as base_path:
        args = Mock()
        args.path = os.path.join(base_path, 'path')
        args.install_base = os.path.join(base_path, 'install')
        args.symlink_install = False

        # create source files
        os.makedirs(args.path)
        with open(os.path.join(args.path, 'source.txt'), 'w') as h:
            h.write('content')
        with open(os.path.join(args.path, 'source2.txt'), 'w') as h:
            h.write('content2')

        # copy file
        install(args, 'source.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert not path.is_symlink()
        assert path.read_text() == 'content'

        # skip all symlink tests on Windows for now
        if sys.platform == 'win32':  # pragma: no cover
            return

        # symlink file, removing existing file
        args.symlink_install = True
        install(args, 'source.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert path.is_symlink()
        assert path.samefile(os.path.join(args.path, 'source.txt'))
        assert path.read_text() == 'content'

        # symlink other file, removing existing directory
        os.remove(os.path.join(args.install_base, 'destination.txt'))
        os.makedirs(os.path.join(args.install_base, 'destination.txt'))
        install(args, 'source2.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert path.is_symlink()
        assert path.samefile(os.path.join(args.path, 'source2.txt'))
        assert path.read_text() == 'content2'

        # copy file, removing existing symlink
        args.symlink_install = False
        install(args, 'source.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert not path.is_symlink()
        assert path.read_text() == 'content'

        # symlink file
        os.remove(os.path.join(args.install_base, 'destination.txt'))
        args.symlink_install = True
        install(args, 'source.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert path.is_symlink()
        assert path.samefile(os.path.join(args.path, 'source.txt'))
        assert path.read_text() == 'content'

        # symlink file, same already existing
        install(args, 'source.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert path.is_symlink()
        assert path.samefile(os.path.join(args.path, 'source.txt'))
        assert path.read_text() == 'content'

        # symlink exists, but to a not existing location
        os.remove(os.path.join(args.path, 'source.txt'))
        install(args, 'source2.txt', 'destination.txt')
        path = Path(base_path) / 'install' / 'destination.txt'
        assert path.is_file()
        assert path.is_symlink()
        assert path.samefile(os.path.join(args.path, 'source2.txt'))
