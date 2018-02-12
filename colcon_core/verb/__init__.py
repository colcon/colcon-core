# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

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
