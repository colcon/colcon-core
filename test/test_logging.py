# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import logging
from pathlib import Path
from unittest.mock import Mock

from colcon_core.logging import add_file_handler
from colcon_core.logging import get_effective_console_level
from colcon_core.logging import get_numeric_log_level
from colcon_core.logging import set_logger_level_from_env
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
    log_level = get_numeric_log_level('Warning')
    assert log_level == logging.WARNING

    # invalid string
    with pytest.raises(ValueError) as e:
        get_numeric_log_level('invalid')
    assert str(e.value).endswith(
        'valid names are: CRITICAL, ERROR, WARNING, INFO, DEBUG '
        '(case-insensitive)')

    # negative numeric
    with pytest.raises(ValueError) as e:
        get_numeric_log_level('-1')
    assert str(e.value).endswith('numeric log levels must be positive')


def test_add_file_handler(tmpdir):
    log_path = Path(tmpdir) / 'test_add_file_handler.log'
    log_path.touch()
    logger = logging.getLogger('test_add_file_handler')
    try:
        logger.setLevel(logging.WARN)
        add_file_handler(logger, log_path)
        assert logger.getEffectiveLevel() != logging.WARN
        logger.info('test_add_file_handler')
    finally:
        for handler in logger.handlers:
            logger.removeHandler(handler)
            handler.close()

    # check only that we logged SOMETHING to the file
    assert log_path.stat().st_size > 10


def test_get_effective_console_level(tmpdir):
    logger = logging.getLogger('test_sync_console_log_level')

    # no level set
    level = get_effective_console_level(logger)
    assert level == logger.getEffectiveLevel()

    # change the level to ERROR
    logger.setLevel(logging.ERROR)
    level = get_effective_console_level(logger)
    assert level == logger.getEffectiveLevel() == logging.ERROR

    # after add_file_handler
    log_path = Path(tmpdir) / 'test_add_file_handler.log'
    log_path.touch()
    try:
        add_file_handler(logger, log_path)
        level = get_effective_console_level(logger)
        assert level == logging.ERROR
    finally:
        for handler in logger.handlers:
            logger.removeHandler(handler)
            handler.close()
