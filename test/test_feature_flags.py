# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from unittest.mock import patch

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


@pytest.mark.parametrize(
    'feature_flags_value',
    _FLAGS_TO_TEST,
    indirect=True)
@pytest.mark.usefixtures('feature_flags_value')
def test_flag_is_set():
    assert is_feature_flag_set('foo')


@pytest.mark.parametrize(
    'feature_flags_value',
    (None, *_FLAGS_TO_TEST),
    indirect=True)
@pytest.mark.usefixtures('feature_flags_value')
def test_flag_not_set():
    assert not is_feature_flag_set('')
    assert not is_feature_flag_set('fo')
    assert not is_feature_flag_set('oo')
    assert not is_feature_flag_set('fooo')
    assert not is_feature_flag_set('ffoo')
    assert not is_feature_flag_set('qux')


@pytest.mark.parametrize(
    'feature_flags_value',
    (None, *_FLAGS_TO_TEST),
    indirect=True)
@pytest.mark.usefixtures('feature_flags_value')
def test_get_flags(feature_flags_value):
    assert [
        flag for flag in (feature_flags_value or ()) if flag
    ] == get_feature_flags()
