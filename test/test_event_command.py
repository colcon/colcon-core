# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import sys

from colcon_core.event.command import Command

from .environment_context import EnvironmentContext


def test_command_to_string():
    cmd = ['executable', 'arg1', 'arg2']
    cwd = '/some/path'
    command = Command(cmd, cwd=cwd)
    assert command.to_string() == \
        "Invoking command in '/some/path': executable arg1 arg2"

    env = {
        '_TEST_NEW_KEY': 'new',
        '_TEST_SAME_VALUE': 'same',
        '_TEST_DIFFERENT_VALUE': 'different',
        '_TEST_PREPENDED_VALUE': 'before-base',
        '_TEST_APPENDED_VALUE': 'base-after',
    }
    if sys.platform != 'win32':
        env['PWD'] = '/other/path'
    command = Command(cmd, cwd=cwd, env=env)

    expected = "Invoking command in '/some/path': " \
        '_TEST_APPENDED_VALUE=${_TEST_APPENDED_VALUE}-after ' \
        '_TEST_DIFFERENT_VALUE=different ' \
        '_TEST_NEW_KEY=new ' \
        '_TEST_PREPENDED_VALUE=before-${_TEST_PREPENDED_VALUE} ' \
        'executable arg1 arg2'
    if sys.platform == 'win32':
        expected = expected.replace('${', '%')
        expected = expected.replace('}', '%')
    with EnvironmentContext(
        _TEST_SAME_VALUE='same',
        _TEST_DIFFERENT_VALUE='same',
        _TEST_PREPENDED_VALUE='base',
        _TEST_APPENDED_VALUE='base',
    ):
        assert command.to_string() == expected

    cmd = ['executable', '&&', 'other exec']
    command = Command(cmd, cwd=cwd)
    assert command.to_string() == \
        "Invoking command in '/some/path': executable && other exec"
    command = Command(cmd, cwd=cwd, shell=True)
    if sys.platform != 'win32':
        assert command.to_string() == \
            "Invoking command in '/some/path': executable && 'other exec'"
    else:
        assert command.to_string() == \
            "Invoking command in '/some/path': " \
            'executable && "other exec"'
