# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import copy
import traceback
from typing import Dict
from typing import TypeVar

from colcon_core.logging import colcon_logger
from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_grouped_by_priority

logger = colcon_logger.getChild(__name__)


class IgnoreLocationException(Exception):
    """
    Exception to signal that a path should be skipped.

    This also excludes all recursive subdirectories from being considered.

    It should be raised in the
    :function:`PackageIdentificationExtensionPoint.identify` method of package
    identification extensions.
    """

    pass


class PackageIdentificationExtensionPoint:
    """
    The interface for package identification extensions.

    A package identification extension populates a package descriptor if a
    given location contains a package.

    For each instance the attribute `PACKAGE_IDENTIFICATION_NAME` is being set
    to the basename of the entry point registering the extension.
    """

    """The version of the package identification extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of package identification extensions."""
    PRIORITY = 100

    def identify(self, desc: PackageDescriptor):
        """
        Check if the given path contains a package.

        If yes, update the package descriptor with additional information.
        If the descriptor already has a package type only act if the type
        matches this extension.

        This method must be overridden in a subclass.

        :param desc: The package descriptor with the directory to check
        :type desc:
          :py:class:`colcon_core.package_descriptor.PackageDescriptor`
        :raises IgnoreLocationException: Skip the path as well as all recursive
          subdirectories
        """
        raise NotImplementedError()


def get_package_identification_extensions():
    """
    Get the available package identification extensions.

    The extensions are grouped by their priority and each group is ordered by
    the entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.PACKAGE_IDENTIFICATION_NAME = name
    return order_extensions_grouped_by_priority(extensions)


ReturnType = TypeVar('ReturnType', None, bool, PackageDescriptor)


def identify(
    extensions: Dict[  # actually an OrderedDict
        int,  # priority
        Dict[str, PackageIdentificationExtensionPoint],  # an OrderedDict
    ],
    path: str,
) -> ReturnType:
    """
    Identify the package in the given path.

    :param extensions: dict of extensions
    :param path: The path
    """
    desc = PackageDescriptor(path)

    for extensions_same_prio in extensions.values():
        result = _identify(extensions_same_prio, desc)

        # continue with next priority level if no information was contributed
        if result is None:
            continue

        # skip location since identification is ambiguous
        if result is False:
            raise IgnoreLocationException()

        assert isinstance(result, PackageDescriptor), result
        if result.identifies_package():
            return result

        # use incrementally populated descriptor for next priority level
        desc = result

    if getattr(desc, 'type', None) or getattr(desc, 'name', None):
        logger.warning(
            "package '{desc.path}' has type or name but is incomplete"
            .format_map(locals()))
    return None


def _identify(extensions_same_prio, desc):
    logger.log(
        1, '_identify(%s) by extensions %s',
        desc.path, sorted(extensions_same_prio.keys()))
    # collect the optionally modified descriptors from all extensions
    results = {desc}
    for key, extension in extensions_same_prio.items():
        desc2 = copy.deepcopy(desc)
        logger.log(1, "_identify(%s) by extension '%s'", desc.path, key)
        try:
            retval = extension.identify(desc2)
            assert retval is None, 'identify() should return None'
        except IgnoreLocationException:
            logger.log(1, '_identify(%s) ignored', desc.path)
            raise
        except Exception as e:
            # catch exceptions raised in identification extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in package identification extension '
                "'{extension.PACKAGE_IDENTIFICATION_NAME}' in '{desc.path}': "
                '{e}\n{exc}'.format_map(locals()))
            # skip failing extension, continue with next one
            continue

        results.add(desc2)

    # multiple extensions populated the descriptor with different values
    if len(results) > 2:
        logger.warning(
            '_identify({desc.path}) has multiple matches and therefore is '
            'being ignored: '.format_map(locals()) +
            ', '.join(sorted(d.type for d in results if d.type is not None)))
        return False

    # no extension populated the descriptor with any values
    if len(results) == 1:
        return None

    results.remove(desc)
    desc = results.pop()
    logger.debug(
        "Package '{desc.path}' with type '{desc.type}' and name '{desc.name}'"
        .format_map(locals()))
    return desc
