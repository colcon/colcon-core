# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import logging

from colcon_core.logging import get_numeric_log_level
from colcon_core.logging import set_logger_level_from_env
from mock import Mock
import pytest

from .environment_context import EnvironmentContext


def test_set_logger_level_from_env():
    logger = logging.getLogger('test')
    default_level = logger.getEffectiveLevel()

    # not set
    set_logger_level_from_env(logger, 'COLCON_TEST_LOGGER_LEVEL')
    assert logger.getEffectiveLevel() == default_level

    # invalid value
    with EnvironmentContext(COLCON_TEST_LOGGER_LEVEL='invalid'):
        logger.warning = Mock()
        set_logger_level_from_env(logger, 'COLCON_TEST_LOGGER_LEVEL')
        assert logger.warning.call_count == 1
    assert logger.getEffectiveLevel() == default_level

    # valid value
    with EnvironmentContext(COLCON_TEST_LOGGER_LEVEL='debug'):
        set_logger_level_from_env(logger, 'COLCON_TEST_LOGGER_LEVEL')
    assert logger.getEffectiveLevel() == logging.DEBUG


def test_get_numeric_log_level():
    # numeric
    log_level = get_numeric_log_level('10')
    assert log_level == logging.DEBUG

    # string
    log_level = get_numeric_log_level('info')
    assert log_level == logging.INFO

    # string with mixed case
    log_level = get_numeric_log_level('Warn')
    assert log_level == logging.WARN

    # invalid string
    with pytest.raises(ValueError) as e:
        get_numeric_log_level('invalid')
    assert str(e).endswith(
        'valid names are: CRITICAL, ERROR, WARNING, INFO, DEBUG '
        '(case-insensitive)')

    # negative numeric
    with pytest.raises(ValueError) as e:
        get_numeric_log_level('-1')
    assert str(e).endswith('numeric log levels must be positive')
