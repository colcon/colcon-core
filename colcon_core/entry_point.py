# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
import os
import traceback

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.logging import colcon_logger
from pkg_resources import iter_entry_points
from pkg_resources import WorkingSet

"""Environment variable to blacklist extensions"""
EXTENSION_BLACKLIST_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_EXTENSION_BLACKLIST',
    'Blacklist extensions which should not be used')

logger = colcon_logger.getChild(__name__)


"""
The group name for entry points identifying colcon extension points.

While all entry points in this package start with `colcon_core.` other
distributions might define entry points with a different prefix.
Those need to be declared using this group name.
"""
EXTENSION_POINT_GROUP_NAME = 'colcon_core.extension_point'


def get_all_entry_points():
    """
    Get all entry points related to `colcon` and any of its extensions.

    :returns: mapping of entry point names to :class:`pkg_resources.EntryPoint`
      instances
    :rtype: dict
    """
    global EXTENSION_POINT_GROUP_NAME
    colcon_extension_points = get_entry_points(EXTENSION_POINT_GROUP_NAME)

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
                entry_point.group_name = group_name
                if entry_point_name in entry_points[group_name]:
                    previous = entry_points[group_name][entry_point_name]
                    logger.error(
                        "Entry point '{group_name}.{entry_point_name}' is "
                        "declared multiple times, '{entry_point}' overwriting "
                        "'{previous}'".format_map(locals()))
                entry_points[group_name][entry_point_name] = \
                    (dist, entry_point)
    return entry_points


def get_entry_points(group_name):
    """
    Get the entry points for a specific group.

    :param str group_name: the name of the `entry_point` group
    :returns: mapping of group names to dictionaries which map entry point
      names to :class:`pkg_resources.EntryPoint` instances
    :rtype: dict
    """
    entry_points = {}
    for entry_point in iter_entry_points(group=group_name):
        entry_point.group_name = group_name
        if entry_point.name in entry_points:
            previous_entry_point = entry_points[entry_point.name]
            logger.error(
                "Entry point '{group_name}.{entry_point.name}' is declared "
                "multiple times, '{entry_point}' overwriting "
                "'{previous_entry_point}'".format_map(locals()))
        entry_points[entry_point.name] = entry_point
    return entry_points


def load_entry_points(group_name):
    """
    Load the entry points for a specific group.

    :param str group_name: the name of the `entry_point` group
    :returns: mapping of entry point names to loaded entry points
    :rtype: dict
    """
    extension_types = {}
    for entry_point in get_entry_points(group_name).values():
        try:
            extension_type = load_entry_point(entry_point)
        except RuntimeError:
            continue
        except Exception as e:
            # catch exceptions raised when loading entry point
            exc = traceback.format_exc()
            logger.error(
                'Exception loading extension '
                "'{group_name}.{entry_point.name}': {e}\n{exc}"
                .format_map(locals()))
            # skip failing entry point, continue with next one
            continue
        extension_types[entry_point.name] = extension_type
    return extension_types


def load_entry_point(entry_point):
    """
    Load the entry point.

    :param entry_point: the :class:`pkg_resources.EntryPoint` instance
    :returns: the loaded entry point
    :raises RuntimeError: if either the group name or the entry point name is
      listed in the environment variable
      :const:`EXTENSION_BLACKLIST_ENVIRONMENT_VARIABLE`
    """
    global EXTENSION_BLACKLIST_ENVIRONMENT_VARIABLE
    blacklist = os.environ.get(
        EXTENSION_BLACKLIST_ENVIRONMENT_VARIABLE.name, None)
    if blacklist:
        blacklist = blacklist.split(os.pathsep)
        env_var_name = EXTENSION_BLACKLIST_ENVIRONMENT_VARIABLE.name
        if entry_point.group_name in blacklist:
            raise RuntimeError(
                'The entry point group name is listed in the environment '
                "variable '{env_var_name}'".format_map(locals()))
        full_name = '{entry_point.group_name}.{entry_point.name}' \
            .format_map(locals())
        if full_name in blacklist:
            raise RuntimeError(
                'The entry point name is listed in the environment variable '
                "'{env_var_name}'".format_map(locals()))
    return entry_point.load()
