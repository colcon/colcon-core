# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os

from colcon_core.environment_variable import EnvironmentVariable


"""Environment variable to enable feature flags"""
FEATURE_FLAGS_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_FEATURE_FLAGS',
    'Enable pre-production features and behaviors')


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
    return flag in get_feature_flags()
