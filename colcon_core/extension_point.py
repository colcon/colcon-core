# Copyright 2016-2018 Dirk Thomas
# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
import os
import traceback

try:
    from importlib.metadata import distributions
    from importlib.metadata import EntryPoint
    from importlib.metadata import entry_points
except ImportError:
    # TODO: Drop this with Python 3.7 support
    from importlib_metadata import distributions
    from importlib_metadata import EntryPoint
    from importlib_metadata import entry_points

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.logging import colcon_logger

"""Environment variable to block extensions"""
EXTENSION_BLOCKLIST_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_EXTENSION_BLOCKLIST',
    'Block extensions which should not be used')

logger = colcon_logger.getChild(__name__)


"""
The group name for entry points identifying colcon extension points.

While all entry points in this package start with `colcon_core.` other
distributions might define entry points with a different prefix.
Those need to be declared using this group name.
"""
EXTENSION_POINT_GROUP_NAME = 'colcon_core.extension_point'


def get_all_extension_points():
    """
    Get all extension points related to `colcon` and any of its extensions.

    :returns: mapping of extension point groups to dictionaries which map
      extension point names to a tuple of extension point values, dist name,
      and dist version
    :rtype: dict
    """
    global EXTENSION_POINT_GROUP_NAME
    colcon_extension_points = get_extension_points(EXTENSION_POINT_GROUP_NAME)
    colcon_extension_points.setdefault(EXTENSION_POINT_GROUP_NAME, None)

    entry_points = defaultdict(dict)
    seen = set()
    for dist in distributions():
        dist_name = dist.metadata['Name']
        if dist_name in seen:
            continue
        seen.add(dist_name)
        for entry_point in dist.entry_points:
            # skip groups which are not registered as extension points
            if entry_point.group not in colcon_extension_points:
                continue

            if entry_point.name in entry_points[entry_point.group]:
                previous = entry_points[entry_point.group][entry_point.name]
                logger.error(
                    f"Entry point '{entry_point.group}.{entry_point.name}' is "
                    f"declared multiple times, '{entry_point.value}' "
                    f"from '{dist._path}' "
                    f"overwriting '{previous}'")
            entry_points[entry_point.group][entry_point.name] = \
                (entry_point.value, dist_name, dist.version)
    return entry_points


def get_extension_points(group):
    """
    Get the extension points for a specific group.

    :param str group: the name of the extension point group
    :returns: mapping of extension point names to extension point values
    :rtype: dict
    """
    extension_points = {}
    try:
        # Python 3.10 and newer
        query = entry_points(group=group)
    except TypeError:
        query = entry_points().get(group, ())
    for entry_point in query:
        if entry_point.name in extension_points:
            previous_entry_point = extension_points[entry_point.name]
            logger.error(
                f"Entry point '{group}.{entry_point.name}' is declared "
                f"multiple times, '{entry_point.value}' overwriting "
                f"'{previous_entry_point}'")
        extension_points[entry_point.name] = entry_point.value
    return extension_points


def load_extension_points(group, *, excludes=None):
    """
    Load the extension points for a specific group.

    :param str group: the name of the extension point group
    :param iterable excludes: the names of the extension points to exclude
    :returns: mapping of entry point names to loaded entry points
    :rtype: dict
    """
    extension_types = {}
    for name, value in get_extension_points(group).items():
        if excludes and name in excludes:
            continue
        try:
            extension_type = load_extension_point(name, value, group)
        except RuntimeError:
            continue
        except Exception as e:  # noqa: F841
            # catch exceptions raised when loading entry point
            exc = traceback.format_exc()
            logger.error(
                'Exception loading extension '
                f"'{group}.{name}': {e}\n{exc}")
            # skip failing entry point, continue with next one
            continue
        extension_types[name] = extension_type
    return extension_types


def load_extension_point(name, value, group):
    """
    Load the extension point.

    :param name: the name of the extension entry point.
    :param value: the value of the extension entry point.
    :param group: the name of the group the extension entry point is a part of.
    :returns: the loaded entry point
    :raises RuntimeError: if either the group name or the entry point name is
      listed in the environment variable
      :const:`EXTENSION_BLOCKLIST_ENVIRONMENT_VARIABLE`
    """
    global EXTENSION_BLOCKLIST_ENVIRONMENT_VARIABLE
    blocklist = os.environ.get(
        EXTENSION_BLOCKLIST_ENVIRONMENT_VARIABLE.name, None)
    if blocklist:
        blocklist = blocklist.split(os.pathsep)
        if group in blocklist:
            raise RuntimeError(
                'The entry point group name is listed in the environment '
                f"variable '{EXTENSION_BLOCKLIST_ENVIRONMENT_VARIABLE.name}'")
        full_name = f'{group}.{name}'
        if full_name in blocklist:
            raise RuntimeError(
                'The entry point name is listed in the environment variable '
                f"'{EXTENSION_BLOCKLIST_ENVIRONMENT_VARIABLE.name}'")
    return EntryPoint(name, value, group).load()
