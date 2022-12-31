# Copyright 2021 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from colcon_core.dependency_descriptor import DependencyDescriptor
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
    assert not extension.match(context, env, get_setup_data(desc, env))

    # empty test requirements
    desc.dependencies['test'] = {}
    assert not extension.match(context, env, get_setup_data(desc, env))

    # pytest not in test requirements
    desc.dependencies['test'] = {
        DependencyDescriptor('nose'),
    }
    assert not extension.match(context, env, get_setup_data(desc, env))

    # pytest in test requirements
    desc.dependencies['test'] = {
        DependencyDescriptor('pytest'),
    }
    assert extension.match(context, env, get_setup_data(desc, env))
