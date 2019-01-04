# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import copy
import logging
import os
from pathlib import Path

from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_name

logger = colcon_logger.getChild(__name__)


class VerbExtensionPoint:
    """
    The interface for verb extensions.

    A verb extension provides a verb to the command line tool.

    For each instance the attribute `VERB_NAME` is being set to the basename of
    the entry point registering the extension.
    """

    """The version of the verb extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    def add_arguments(self, *, parser):
        """
        Add command line arguments specific to the verb.

        The method is intended to be overridden in a subclass.

        :param parser: The argument parser
        """
        pass

    def main(self, *, context):
        """
        Execute the verb extension logic.

        This method must be overridden in a subclass.

        :param context: The context providing the parsed command line arguments
        :returns: The return code
        """
        raise NotImplementedError()


def get_verb_extensions():
    """
    Get the available verb extensions.

    The extensions are ordered by their entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.VERB_NAME = name
    return order_extensions_by_name(extensions)


def check_and_mark_build_tool(build_base, *, this_build_tool='colcon'):
    """
    Check the marker file for the previous build tool, otherwise create it.

    The marker filename is `.built_by`.

    :param str build_base: The build directory
    :param str this_build_tool: The name of this build tool
    :raises RuntimeError: if the marker file contains the name of a different
      build tool
    """
    marker_path = Path(build_base) / '.built_by'
    if marker_path.parent.is_dir():
        if marker_path.is_file():
            previous_build_tool = marker_path.read_text().rstrip()
            if previous_build_tool == this_build_tool:
                return
            raise RuntimeError(
                "The build directory '{build_base}' was created by "
                "'{previous_build_tool}'. Please remove the build directory "
                'or pick a different one.'.format_map(locals()))
    else:
        os.makedirs(build_base, exist_ok=True)

    marker_path.write_text(this_build_tool + '\n')


def check_and_mark_install_layout(install_base, *, merge_install):
    """
    Check the marker file for the previous install layout, otherwise create it.

    The marker filename is `.colcon_install_layout`.

    :param str install_base: The install directory
    :param bool merge_install: The flag if all packages share the same prefix
    :raises RuntimeError: if the marker file contains a different install
      layout
    """
    this_install_layout = 'merged' if merge_install else 'isolated'
    marker_path = Path(install_base) / '.colcon_install_layout'
    if marker_path.parent.is_dir():
        if marker_path.is_file():
            previous_install_layout = marker_path.read_text().rstrip()
            if previous_install_layout == this_install_layout:
                return
            change_option = 'remove' if merge_install else 'add'
            raise RuntimeError(
                "The install directory '{install_base}' was created with the "
                "layout '{previous_install_layout}'. Please remove the "
                'install directory, pick a different one or {change_option} '
                "the '--merge-install' option.".format_map(locals()))
    else:
        try:
            os.makedirs(install_base, exist_ok=True)
        except FileExistsError:
            raise RuntimeError(
                "The install base '{install_base}' is not a directory"
                .format_map(locals()))

    marker_path.write_text(this_install_layout + '\n')


def update_object(
    object_, key, value, package_name, argument_type, value_source
):
    """
    Set or update an attribute of an object.

    If the attribute exists and the passed value as well as the current value
    of the attribute are dictionaries then the current values are being updated
    with the passed values.

    If the attribute exists and the passed value as well as the current value
    of the attribute are lists then the passed values are being appended to the
    current values.

    Otherwise the attribute is being set to the passed value potentially
    overwriting an existing value.

    :param key: The name of the attributes
    :param value: The value used to set or update the attribute
    :param str package_name: The package name, only used for log messages
    :param str argument_type: The argument type, only used in log messages
    :param str value_source: The source of the value, only used for log
      messages
    """
    if not hasattr(object_, key):
        logger.log(
            5, "set package '{package_name}' {argument_type} argument '{key}' "
            "from {value_source} to '{value}'".format_map(locals()))
        # add value to the object
        # copy value to avoid changes to either of them to affect each other
        setattr(object_, key, copy.deepcopy(value))
        return

    old_value = getattr(object_, key)
    if isinstance(old_value, dict) and isinstance(value, dict):
        logger.log(
            5, "update package '{package_name}' {argument_type} argument "
            "'{key}' from {value_source} with '{value}'".format_map(locals()))
        # update dictionary
        old_value.update(value)
        return

    if isinstance(old_value, list) and isinstance(value, list):
        logger.log(
            5, "extend package '{package_name}' {argument_type} argument "
            "'{key}' from {value_source} with '{value}'".format_map(locals()))
        # extend list
        old_value += value
        return

    severity = 5 \
        if old_value is None or type(old_value) == type(value) \
        else logging.WARNING
    logger.log(
        severity, "overwrite package '{package_name}' {argument_type} "
        "argument '{key}' from {value_source} with '{value}' (before: "
        "'{old_value}')".format_map(locals()))
    # overwrite existing value
    # copy value to avoid changes to either of them to affect each other
    setattr(object_, key, copy.deepcopy(value))
