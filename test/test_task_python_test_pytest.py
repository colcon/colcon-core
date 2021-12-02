# Copyright 2021 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.task import TaskContext
from colcon_core.task.python import get_setup_data
from colcon_core.task.python.test.pytest import PytestPythonTestingStep


def test_pytest_match():
    extension = PytestPythonTestingStep()
    env = {}
    desc = PackageDescriptor('/dev/null')
    context = TaskContext(pkg=desc, args=None, dependencies=None)

    desc.name = 'pkg-name'
    desc.type = 'python'

    # no test requirements
    desc.metadata['get_python_setup_options'] = lambda env: {}
    assert not extension.match(context, env, get_setup_data(desc, env))

    # pytest not in tests_require
    desc.metadata['get_python_setup_options'] = lambda env: {
        'tests_require': ['nose'],
    }
    assert not extension.match(context, env, get_setup_data(desc, env))

    # pytest not in extras_require.test
    desc.metadata['get_python_setup_options'] = lambda env: {
        'extras_require': {
            'test': ['nose']
        },
    }
    assert not extension.match(context, env, get_setup_data(desc, env))

    # pytest in tests_require
    desc.metadata['get_python_setup_options'] = lambda env: {
        'tests_require': ['pytest'],
    }
    assert extension.match(context, env, get_setup_data(desc, env))

    # pytest in extras_require.test
    desc.metadata['get_python_setup_options'] = lambda env: {
        'extras_require': {
            'test': ['pytest']
        },
    }
    assert extension.match(context, env, get_setup_data(desc, env))
