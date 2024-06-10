# Copyright 2016-2018 Dirk Thomas
# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from unittest.mock import DEFAULT
from unittest.mock import patch

try:
    from importlib.metadata import Distribution
except ImportError:
    # TODO: Drop this with Python 3.7 support
    from importlib_metadata import Distribution

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


class _FakeDistribution(Distribution):

    def __init__(self, entry_points):
        entry_points_spec = []
        for group_name, group_members in entry_points.items():
            entry_points_spec.append(f'[{group_name}]')
            for member_name, member_value in group_members:
                entry_points_spec.append(f'{member_name} = {member_value}')
            entry_points_spec.append('')

        self._files = {
            'PKG-INFO': f'Name: dist-{id(self)}\nVersion: 0.0.0\n',
            'entry_points.txt': '\n'.join(entry_points_spec) + '\n',
        }

    def read_text(self, filename):
        return self._files.get(filename)

    def locate_file(self, path):
        return path


def _distributions():
    yield _FakeDistribution({
        EXTENSION_POINT_GROUP_NAME: [('group1', 'g1')],
        'group1': [('extA', 'eA'), ('extB', 'eB')],
    })
    yield _FakeDistribution({
        EXTENSION_POINT_GROUP_NAME: [('group2', 'g2')],
        'group2': [('extC', 'eC')],
    })
    yield _FakeDistribution({
        'groupX': [('extD', 'eD')],
    })


def _entry_points():
    for dist in _distributions():
        yield from dist.entry_points


def test_all_extension_points():
    with patch(
        'colcon_core.extension_point.entry_points',
        side_effect=_entry_points
    ):
        with patch(
            'colcon_core.extension_point.distributions',
            side_effect=_distributions
        ):
            clear_entry_point_cache()

            # successfully load a known entry point
            extension_points = get_all_extension_points()
            assert set(extension_points.keys()) == {
                EXTENSION_POINT_GROUP_NAME,
                'group1',
                'group2',
            }
            assert set(extension_points['group1'].keys()) == {'extA', 'extB'}
            assert extension_points['group1']['extA'][0] == 'eA'


def test_extension_point_blocklist():
    # successful loading of extension point without a blocklist
    with patch(
        'colcon_core.extension_point.entry_points',
        side_effect=_entry_points
    ):
        with patch(
            'colcon_core.extension_point.distributions',
            side_effect=_distributions
        ):
            clear_entry_point_cache()
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


def test_redefined_extension_point():
    def _duped_distributions():
        yield from _distributions()
        yield _FakeDistribution({
            'group2': [('extC', 'eC-prime')],
        })

    def _duped_entry_points():
        for dist in _duped_distributions():
            yield from dist.entry_points

    with patch('colcon_core.extension_point.logger.error') as error:
        with patch(
            'colcon_core.extension_point.entry_points',
            side_effect=_duped_entry_points
        ):
            with patch(
                'colcon_core.extension_point.distributions',
                side_effect=_duped_distributions
            ):
                clear_entry_point_cache()
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
