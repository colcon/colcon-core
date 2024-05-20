# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from unittest.mock import patch

from colcon_core.feature_flags import check_implemented_flags
from colcon_core.feature_flags import FEATURE_FLAGS_ENVIRONMENT_VARIABLE
from colcon_core.feature_flags import get_feature_flags
from colcon_core.feature_flags import is_feature_flag_set
import pytest


_FLAGS_TO_TEST = (
    ('foo',),
    ('foo', 'foo'),
    ('foo', ''),
    ('', 'foo'),
    ('', 'foo', ''),
    ('foo', 'bar'),
    ('bar', 'foo'),
    ('bar', 'foo', 'baz'),
)


@pytest.fixture
def feature_flags_value(request):
    env = dict(os.environ)
    if request.param is not None:
        env[FEATURE_FLAGS_ENVIRONMENT_VARIABLE.name] = os.pathsep.join(
            request.param)
    else:
        env.pop(FEATURE_FLAGS_ENVIRONMENT_VARIABLE.name, None)

    mock_env = patch('colcon_core.feature_flags.os.environ', env)
    request.addfinalizer(mock_env.stop)
    mock_env.start()
    return request.param


@pytest.fixture
def feature_flag_reports(request):
    reported_uses = patch('colcon_core.feature_flags._REPORTED_USES', set())
    request.addfinalizer(reported_uses.stop)
    reported_uses.start()
    return reported_uses


@pytest.mark.parametrize(
    'feature_flags_value',
    _FLAGS_TO_TEST,
    indirect=True)
@pytest.mark.usefixtures('feature_flags_value', 'feature_flag_reports')
def test_flag_is_set():
    with patch('colcon_core.feature_flags.logger.warning') as warn:
        assert is_feature_flag_set('foo')
        assert warn.call_count == 2
        assert is_feature_flag_set('foo')
        assert warn.call_count == 2


@pytest.mark.parametrize(
    'feature_flags_value',
    (None, *_FLAGS_TO_TEST),
    indirect=True)
@pytest.mark.usefixtures('feature_flags_value', 'feature_flag_reports')
def test_flag_not_set():
    with patch('colcon_core.feature_flags.logger.warning') as warn:
        assert not is_feature_flag_set('')
        assert not is_feature_flag_set('fo')
        assert not is_feature_flag_set('oo')
        assert not is_feature_flag_set('fooo')
        assert not is_feature_flag_set('ffoo')
        assert not is_feature_flag_set('qux')
        assert warn.call_count == 0


@pytest.mark.parametrize(
    'feature_flags_value',
    (None, *_FLAGS_TO_TEST),
    indirect=True)
@pytest.mark.usefixtures('feature_flags_value')
def test_get_flags(feature_flags_value):
    assert [
        flag for flag in (feature_flags_value or ()) if flag
    ] == get_feature_flags()


@pytest.mark.parametrize('feature_flags_value', (('baz',),), indirect=True)
@pytest.mark.usefixtures('feature_flags_value')
def test_implemented():
    with patch('colcon_core.feature_flags.IMPLEMENTED_FLAGS', {'foo'}):
        with patch('colcon_core.feature_flags.logger.warning') as warn:
            assert not is_feature_flag_set('bar')
            assert warn.call_count == 0
            assert is_feature_flag_set('baz')
            assert warn.call_count == 2
            assert is_feature_flag_set('foo')
            assert warn.call_count == 2
            check_implemented_flags()
            assert warn.call_count == 2

    with patch('colcon_core.feature_flags.IMPLEMENTED_FLAGS', {'baz'}):
        with patch('colcon_core.feature_flags.logger.warning') as warn:
            check_implemented_flags()
            assert warn.call_count == 1
