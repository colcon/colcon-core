# Copyright 2016-2018 Dirk Thomas
# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from unittest.mock import DEFAULT
from unittest.mock import patch

from colcon_core.extension_point import EntryPoint
from colcon_core.extension_point import EXTENSION_POINT_GROUP_NAME
from colcon_core.extension_point import get_all_extension_points
from colcon_core.extension_point import get_extension_points
from colcon_core.extension_point import load_extension_point
from colcon_core.extension_point import load_extension_points
import pytest

from .environment_context import EnvironmentContext


Group1 = EntryPoint('group1', 'g1')
Group2 = EntryPoint('group2', 'g2')


class Dist():

    project_name = 'dist'

    def __init__(self, group_name, group):
        self._group_name = group_name
        self._group = group

    def __lt__(self, other):
        return self._group_name < other._group_name

    def get_entry_map(self):
        return self._group


def iter_entry_points(*, group):
    if group == EXTENSION_POINT_GROUP_NAME:
        return [Group1, Group2]
    assert group == Group1.name
    ep1 = EntryPoint('extA', 'eA')
    ep2 = EntryPoint('extB', 'eB')
    return [ep1, ep2]


def working_set():
    return [
        Dist('group1', {
            'group1': {ep.name: ep for ep in iter_entry_points(group='group1')}
        }),
        Dist('group2', {'group2': {'extC': EntryPoint('extC', 'eC')}}),
        Dist('groupX', {'groupX': {'extD': EntryPoint('extD', 'eD')}}),
    ]


def test_all_extension_points():
    with patch(
        'colcon_core.extension_point.iter_entry_points',
        side_effect=iter_entry_points
    ):
        with patch(
            'colcon_core.extension_point.WorkingSet',
            side_effect=working_set
        ):
            # successfully load a known entry point
            extension_points = get_all_extension_points()
            assert set(extension_points.keys()) == {'group1', 'group2'}
            assert set(extension_points['group1'].keys()) == {'extA', 'extB'}
            assert extension_points['group1']['extA'] == (
                'eA', Dist.project_name, None)


def test_extension_point_blocklist():
    # successful loading of extension point without a blocklist
    with patch(
        'colcon_core.extension_point.iter_entry_points',
        side_effect=iter_entry_points
    ):
        with patch(
            'colcon_core.extension_point.WorkingSet',
            side_effect=working_set
        ):
            extension_points = get_extension_points('group1')
    assert 'extA' in extension_points.keys()
    extension_point = extension_points['extA']
    assert extension_point == 'eA'

    with patch.object(EntryPoint, 'resolve', return_value=None) as resolve:
        load_extension_point('extA', 'eA', 'group1')
        assert resolve.call_count == 1

        # successful loading of entry point not in blocklist
        resolve.reset_mock()
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST=os.pathsep.join([
            'group1.extB', 'group2.extC'])
        ):
            load_extension_point('extA', 'eA', 'group1')
        assert resolve.call_count == 1

        # entry point in a blocked group can't be loaded
        resolve.reset_mock()
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST='group1'):
            with pytest.raises(RuntimeError) as e:
                load_extension_point('extA', 'eA', 'group1')
            assert 'The entry point group name is listed in the environment ' \
                'variable' in str(e.value)
        assert resolve.call_count == 0

        # entry point listed in the blocklist can't be loaded
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST=os.pathsep.join([
            'group1.extA', 'group1.extB'])
        ):
            with pytest.raises(RuntimeError) as e:
                load_extension_point('extA', 'eA', 'group1')
            assert 'The entry point name is listed in the environment ' \
                'variable' in str(e.value)
        assert resolve.call_count == 0


def entry_point_resolve(self, *args, **kwargs):
    if self.name == 'exception':
        raise Exception('entry point raising exception')
    if self.name == 'runtime_error':
        raise RuntimeError('entry point raising runtime error')
    elif self.name == 'success':
        return
    return DEFAULT


@patch.object(EntryPoint, 'resolve', entry_point_resolve)
@patch(
    'colcon_core.extension_point.get_extension_points',
    return_value={'exception': 'a', 'runtime_error': 'b', 'success': 'c'}
)
def test_load_extension_points_with_exception(_):
    with patch('colcon_core.extension_point.logger.error') as error:
        extensions = load_extension_points('group')
    # the extension point raising an exception different than a runtime error
    # results in an error message
    assert error.call_count == 1
    assert len(error.call_args[0]) == 1
    assert "Exception loading extension 'group.exception'" \
        in error.call_args[0][0]
    assert 'entry point raising exception' in error.call_args[0][0]
    # neither of the extension points was loaded successfully
    assert extensions == {'success': None}
