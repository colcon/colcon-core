# Copyright 2016-2018 Dirk Thomas
# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
import os
import traceback

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.logging import colcon_logger
from pkg_resources import EntryPoint
from pkg_resources import iter_entry_points
from pkg_resources import WorkingSet

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
    working_set = WorkingSet()
    for dist in sorted(working_set):
        entry_map = dist.get_entry_map()
        for group_name in entry_map.keys():
            # skip groups which are not registered as extension points
            if group_name not in colcon_extension_points:
                continue

            group = entry_map[group_name]
            for entry_point_name, entry_point in group.items():
                if entry_point_name in entry_points[group_name]:
                    previous = entry_points[group_name][entry_point_name]
                    logger.error(
                        f"Entry point '{group_name}.{entry_point_name}' is "
                        f"declared multiple times, '{entry_point}' "
                        f"overwriting '{previous}'")
                value = entry_point.module_name
                if entry_point.attrs:
                    value += f":{'.'.join(entry_point.attrs)}"
                entry_points[group_name][entry_point_name] = (
                    value, dist.project_name, getattr(dist, 'version', None))
    return entry_points


def get_extension_points(group):
    """
    Get the extension points for a specific group.

    :param str group: the name of the extension point group
    :returns: mapping of extension point names to extension point values
    :rtype: dict
    """
    entry_points = {}
    for entry_point in iter_entry_points(group=group):
        if entry_point.name in entry_points:
            previous_entry_point = entry_points[entry_point.name]
            logger.error(
                f"Entry point '{group}.{entry_point.name}' is declared "
                f"multiple times, '{entry_point}' overwriting "
                f"'{previous_entry_point}'")
        value = entry_point.module_name
        if entry_point.attrs:
            value += f":{'.'.join(entry_point.attrs)}"
        entry_points[entry_point.name] = value
    return entry_points


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
    if ':' in value:
        module_name, attr = value.split(':', 1)
        attrs = attr.split('.')
    else:
        module_name = value
        attrs = ()
    return EntryPoint(name, module_name, attrs).resolve()
