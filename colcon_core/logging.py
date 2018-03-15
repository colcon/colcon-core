# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import logging
import os

logging.basicConfig()
colcon_logger = logging.getLogger('colcon')

try:
    import coloredlogs
except ImportError:  # pragma: no cover
    pass
else:
    log_format = os.environ.get(
        'COLOREDLOGS_LOG_FORMAT', '%(name)s %(levelname)s %(message)s')
    coloredlogs.install(level=1, logger=colcon_logger, fmt=log_format)


def set_logger_level_from_env(logger, env_name):
    """
    Set the log level based on an environment variable.

    A warning message is logged if the environment variable has an unsupported
    value.

    :param logger: The logger
    :param str env_var: The name of the environment variable
    """
    log_level = os.environ.get(env_name)
    if log_level:
        try:
            numeric_log_level = get_numeric_log_level(log_level)
        except ValueError as e:
            logger.warn(
                "environment variable '{env_name}' has unsupported value "
                "'{log_level}', {e}".format_map(locals()))
        else:
            logger.setLevel(numeric_log_level)


def get_numeric_log_level(value):
    """
    Convert a log level into a numeric value.

    :param value: The log level can be either a string (case insensitive) or a
      positive number
    :returns: The numeric value
    :rtype: int
    :raises ValueError: if the log level string is not one of the valid names
      (`CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`) or if the numeric value
      is zero or negative
    """
    try:
        value = int(value)
    except ValueError:
        string_value = value.upper()
        value = logging.getLevelName(string_value)
        if value == 'Level ' + string_value:
            raise ValueError(
                'valid names are: CRITICAL, ERROR, WARNING, INFO, DEBUG '
                '(case-insensitive)')
    else:
        if value < 1:
            raise ValueError('numeric log levels must be positive')
    return value
