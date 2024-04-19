# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.logging import colcon_logger

logger = colcon_logger.getChild(__name__)

"""Environment variable to enable feature flags"""
FEATURE_FLAGS_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_FEATURE_FLAGS',
    'Enable pre-production features and behaviors')

_REPORTED_USES = set()


def get_feature_flags():
    """
    Retrieve all enabled feature flags.

    :returns: List of enabled flags
    :rtype: list
    """
    return [
        flag for flag in (
            os.environ.get(FEATURE_FLAGS_ENVIRONMENT_VARIABLE.name) or ''
        ).split(os.pathsep) if flag
    ]


def is_feature_flag_set(flag):
    """
    Determine if a specific feature flag is enabled.

    Feature flags are case-sensitive and separated by the os-specific path
    separator character.

    :param str flag: Name of the flag to search for

    :returns: True if the flag is set
    :rtype: bool
    """
    if flag in get_feature_flags():
        if flag not in _REPORTED_USES:
            logger.warning(f'Enabling feature: {flag}')
            _REPORTED_USES.add(flag)
        return True
    return False
