# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os

from colcon_core.entry_point import EXTENSION_POINT_GROUP_NAME
from colcon_core.entry_point import get_all_entry_points
from colcon_core.entry_point import get_entry_points
from colcon_core.entry_point import load_entry_point
from colcon_core.entry_point import load_entry_points
from mock import Mock
from mock import patch
import pytest

from .environment_context import EnvironmentContext


class Group1:
    name = 'group1'


class Group2:
    name = 'group2'


class Dist():

    def __init__(self, group_name, group):
        self._group_name = group_name
        self._group = group

    def __lt__(self, other):
        return self._group_name < other._group_name

    def get_entry_map(self):
        return self._group


class EntryPoint:
    pass


def iter_entry_points(*, group):
    if group == EXTENSION_POINT_GROUP_NAME:
        return [Group1, Group2]
    assert group == Group1.name
    ep1 = EntryPoint()
    ep1.name = 'extA'
    ep2 = EntryPoint()
    ep2.name = 'extB'
    return [ep1, ep2]


def working_set():
    return [
        Dist('group1', {
            'group1': {ep.name: ep for ep in iter_entry_points(group='group1')}
        }),
        Dist('group2', {'group2': {'extC': EntryPoint()}}),
        Dist('other_group', {'other_group': {'extD': EntryPoint()}}),
    ]


def test_all_entry_points():
    with patch(
        'colcon_core.entry_point.iter_entry_points',
        side_effect=iter_entry_points
    ):
        with patch(
            'colcon_core.entry_point.WorkingSet',
            side_effect=working_set
        ):
            # successfully load a known entry point
            assert set(get_all_entry_points().keys()) == {'group1', 'group2'}
            assert set(get_all_entry_points()['group1'].keys()) == \
                {'extA', 'extB'}
            assert len(get_all_entry_points()['group1']['extA']) == 2
            assert isinstance(
                get_all_entry_points()['group1']['extA'][1], EntryPoint)
            assert get_all_entry_points()['group1']['extA'][1] .group_name == \
                'group1'
            assert get_all_entry_points()['group1']['extA'][1] .name == 'extA'


def test_entry_point_blacklist():
    # successful loading of entry point without a blacklist
    with patch(
        'colcon_core.entry_point.iter_entry_points',
        side_effect=iter_entry_points
    ):
        with patch(
            'colcon_core.entry_point.WorkingSet',
            side_effect=working_set
        ):
            entry_points = get_entry_points('group1')
    assert 'extA' in entry_points.keys()
    entry_point = entry_points['extA']
    assert entry_point.group_name == 'group1'
    assert entry_point.name == 'extA'

    entry_point.load = Mock()
    assert isinstance(entry_point, EntryPoint)
    load_entry_point(entry_point)
    assert entry_point.load.call_count == 1

    # successful loading of entry point not in blacklist
    entry_point.load.reset_mock()
    with EnvironmentContext(COLCON_EXTENSION_BLACKLIST=os.pathsep.join([
        'group1.extB', 'group2.extC'])
    ):
        load_entry_point(entry_point)
    assert entry_point.load.call_count == 1

    # entry point in a blacklisted group can't be loaded
    entry_point.load.reset_mock()
    with EnvironmentContext(COLCON_EXTENSION_BLACKLIST='group1'):
        with pytest.raises(RuntimeError) as e:
            load_entry_point(entry_point)
        assert 'The entry point group name is listed in the environment ' \
            'variable' in str(e)
    assert entry_point.load.call_count == 0

    # entry point listed in the blacklist can't be loaded
    with EnvironmentContext(COLCON_EXTENSION_BLACKLIST=os.pathsep.join([
        'group1.extA', 'group1.extB'])
    ):
        with pytest.raises(RuntimeError) as e:
            load_entry_point(entry_point)
        assert 'The entry point name is listed in the environment variable' \
            in str(e)
    assert entry_point.load.call_count == 0


# mock entry points
class EntryPointRaisingException:
    group_name = 'group'
    name = 'exception'

    def load(self):
        raise Exception('entry point raising exception')


class EntryPointRaisingRuntimeError:
    group_name = 'group'
    name = 'runtime_error'

    def load(self):
        raise RuntimeError('entry point raising runtime error')


class EntryPointSuccess:
    group_name = 'group'
    name = 'success'

    def load(self):
        pass


@patch(
    'colcon_core.entry_point.get_entry_points',
    return_value={
        EntryPointRaisingException.name: EntryPointRaisingException(),
        EntryPointRaisingRuntimeError.name: EntryPointRaisingRuntimeError(),
        EntryPointSuccess.name: EntryPointSuccess(),
    })
def test_load_entry_points_with_exception(_):
    with patch('colcon_core.entry_point.logger.error') as error:
        extensions = load_entry_points('group')
    # the entry point raising an exception different than a runtime error
    # results in an error message
    assert error.call_count == 1
    assert len(error.call_args[0]) == 1
    assert "Exception loading extension 'group.exception'" \
        in error.call_args[0][0]
    assert 'entry point raising exception' in error.call_args[0][0]
    # neither of the entry points was loaded successfully
    assert extensions == {'success': None}
