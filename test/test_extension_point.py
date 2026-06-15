# Copyright 2016-2018 Dirk Thomas
# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
import sys
from unittest.mock import DEFAULT
from unittest.mock import patch

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.extension_point import clear_entry_point_cache
from colcon_core.extension_point import EntryPoint
from colcon_core.extension_point import EXTENSION_POINT_GROUP_NAME
from colcon_core.extension_point import get_all_extension_points
from colcon_core.extension_point import get_extension_points
from colcon_core.extension_point import load_extension_point
from colcon_core.extension_point import load_extension_points
from colcon_core.extension_point import override_blocklist_variable
import pytest

from .environment_context import EnvironmentContext


@pytest.fixture(autouse=True)
def clear_cache():
    clear_entry_point_cache()
    try:
        yield
    finally:
        clear_entry_point_cache()


@pytest.fixture(scope='module', autouse=True)
def mock_dist_path():
    dist1_path = os.path.join(os.path.dirname(__file__), 'mock_dist', 'dist1')
    with patch('sys.path', [*sys.path, dist1_path]):
        yield dist1_path


@pytest.fixture
def redefined_extension_point_path(mock_dist_path):
    dist2_path = os.path.join(os.path.dirname(__file__), 'mock_dist', 'dist2')
    with patch('sys.path', [*sys.path, dist2_path]):
        # Sanity check - we need both of the mock distributions on sys.path
        assert mock_dist_path in sys.path
        yield dist2_path


def test_all_extension_points():
    # successfully load a known entry point
    extension_points = get_all_extension_points()
    assert {
        EXTENSION_POINT_GROUP_NAME,
        'group1',
        'group2',
    } <= set(extension_points.keys())
    assert set(extension_points['group1'].keys()) == {'extA', 'extB'}
    assert extension_points['group1']['extA'] == (
        'eA', 'colcon-mock-dist1', '1.0')


def test_extension_point_blocklist():
    # successful loading of extension point without a blocklist
    extension_points = get_extension_points('group1')
    assert 'extA' in extension_points.keys()
    extension_point = extension_points['extA']
    assert extension_point == 'eA'

    with patch.object(EntryPoint, 'load', return_value=None) as load:
        clear_entry_point_cache()
        load_extension_point('extA', 'eA', 'group1')
        assert load.call_count == 1

        # successful loading of entry point not in blocklist
        load.reset_mock()
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST=os.pathsep.join([
            'group1.extB', 'group2.extC'])
        ):
            clear_entry_point_cache()
            load_extension_point('extA', 'eA', 'group1')
        assert load.call_count == 1

        # entry point in a blocked group can't be loaded
        load.reset_mock()
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST='group1'):
            clear_entry_point_cache()
            with pytest.raises(RuntimeError) as e:
                load_extension_point('extA', 'eA', 'group1')
            assert 'The entry point group name is listed in the environment ' \
                'variable' in str(e.value)
        assert load.call_count == 0

        # entry point listed in the blocklist can't be loaded
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST=os.pathsep.join([
            'group1.extA', 'group1.extB'])
        ):
            clear_entry_point_cache()
            with pytest.raises(RuntimeError) as e:
                load_extension_point('extA', 'eA', 'group1')
            assert 'The entry point name is listed in the environment ' \
                'variable' in str(e.value)
        assert load.call_count == 0


def test_extension_point_blocklist_override():
    with patch.object(EntryPoint, 'load', return_value=None) as load:
        clear_entry_point_cache()

        my_extension_blocklist = EnvironmentVariable(
            'MY_EXTENSION_BLOCKLIST', 'Foo bar baz')
        override_blocklist_variable(my_extension_blocklist)

        try:
            # entry point in default blocklist variable can be loaded
            load.reset_mock()
            with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST='group1'):
                clear_entry_point_cache()
                load_extension_point('extA', 'eA', 'group1')
            assert load.call_count == 1

            # entry point in custom blocklist variable can't be loaded
            load.reset_mock()
            with EnvironmentContext(MY_EXTENSION_BLOCKLIST='group1'):
                clear_entry_point_cache()
                with pytest.raises(RuntimeError) as e:
                    load_extension_point('extA', 'eA', 'group1')
                assert 'The entry point group name is listed in the ' \
                    'environment variable' in str(e.value)
            assert load.call_count == 0
        finally:
            override_blocklist_variable(None)

        # entry point in default blocklist variable can no longer be loaded
        load.reset_mock()
        with EnvironmentContext(COLCON_EXTENSION_BLOCKLIST='group1'):
            clear_entry_point_cache()
            with pytest.raises(RuntimeError) as e:
                load_extension_point('extA', 'eA', 'group1')
            assert 'The entry point group name is listed in the ' \
                'environment variable' in str(e.value)
        assert load.call_count == 0


def test_redefined_extension_point(redefined_extension_point_path):
    with patch('colcon_core.extension_point.logger.error') as error:
        extension_points = get_all_extension_points()
        assert 'eC-prime' == extension_points['group2']['extC'][0]
        assert error.call_count == 1

        error.reset_mock()
        clear_entry_point_cache()

        extension_points = get_extension_points('group2')
        assert 'eC-prime' == extension_points.get('extC')
        assert error.call_count == 1


def entry_point_load(self, *args, **kwargs):
    if self.name == 'exception':
        raise Exception('entry point raising exception')
    if self.name == 'runtime_error':
        raise RuntimeError('entry point raising runtime error')
    elif self.name == 'success':
        return
    return DEFAULT


@patch.object(EntryPoint, 'load', entry_point_load)
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
