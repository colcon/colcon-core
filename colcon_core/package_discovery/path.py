# Copyright 2016-2020 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from glob import glob
import os
import sys

from colcon_core.argument_default import is_default_value
from colcon_core.argument_default import wrap_default_value
from colcon_core.package_discovery import logger
from colcon_core.package_discovery import PackageDiscoveryExtensionPoint
from colcon_core.package_identification import identify
from colcon_core.package_identification import IgnoreLocationException
from colcon_core.plugin_system import satisfies_version


class PathPackageDiscovery(PackageDiscoveryExtensionPoint):
    """Check specific paths for packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            PackageDiscoveryExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def has_default(self):  # noqa: D102
        return True

    def add_arguments(  # noqa: D102
        self, *, parser, with_default, single_path=False
    ):
        parser.add_argument(
            '--paths',
            nargs='*' if not single_path else '?',
            metavar='PATH',
            default=wrap_default_value(['.']) if with_default else None,
            help='The paths to check for a package. Use shell wildcards '
                 '(e.g. `src/*`) to select all direct subdirectories' +
                 (' (default: .)' if with_default else ''))

    def has_parameters(self, *, args):  # noqa: D102
        return not is_default_value(args.paths) and \
            bool(args.paths)

    def discover(self, *, args, identification_extensions):  # noqa: D102
        if args.paths is None:
            return set()

        # on Windows manually check for wildcards and expand them
        if sys.platform == 'win32':
            _expand_wildcards(args.paths)

        logger.log(1, 'PathPackageDiscovery.discover(%s)', args.paths)

        visited_paths = set()
        descs = set()
        for path in args.paths:
            real_path = os.path.realpath(path)
            # avoid recrawling same paths
            if real_path in visited_paths:
                continue
            visited_paths.add(real_path)

            try:
                result = identify(identification_extensions, path)
            except IgnoreLocationException:
                continue
            if result:
                descs.add(result)

        return descs


def _expand_wildcards(paths):
    """
    Expand wildcards explicitly.

    This is only necessary on Windows.

    :param list paths: The paths to update in place
    """
    i = 0
    while i < len(paths):
        path = paths[i]
        if '*' not in path:
            i += 1
            continue
        expanded_paths = [
            p for p in sorted(glob(path))
            if os.path.isdir(p)]
        logger.log(
            5, "PathPackageDiscovery.discover() expanding '%s' to %s",
            path, expanded_paths)
        paths[i:i + 1] = expanded_paths
        i += len(expanded_paths)
