# Copyright 2020 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.argument_default import is_default_value
from colcon_core.argument_default import unwrap_default_value
from colcon_core.argument_default import wrap_default_value
import pytest


def test_argument_default():
    values = [
        True,
        [1, 2, 3],
        'foo',
    ]
    for value in values:
        assert not is_default_value(value)
        with pytest.raises(ValueError):
            unwrap_default_value(value)
        default_value = wrap_default_value(value)
        assert is_default_value(default_value)
        assert type(default_value) != type(value)
        with pytest.raises(ValueError):
            wrap_default_value(default_value)
        unwrapped_value = unwrap_default_value(default_value)
        assert value == unwrapped_value

    value = 42
    unchanged_value = wrap_default_value(value)
    assert type(unchanged_value) == type(value)
    assert unchanged_value == value
