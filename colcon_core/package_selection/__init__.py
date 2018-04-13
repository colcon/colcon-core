# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import traceback

from colcon_core.logging import colcon_logger
from colcon_core.package_augmentation import augment_packages
from colcon_core.package_discovery import add_package_discovery_arguments
from colcon_core.package_discovery import discover_packages
from colcon_core.package_identification \
    import get_package_identification_extensions
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_name
from colcon_core.topological_order import topological_order_packages

logger = colcon_logger.getChild(__name__)


class PackageSelectionExtensionPoint:
    """
    The interface for package selection extensions.

    A package selection extension determines the subset of packages to be
    processed.

    For each instance the attribute `PACKAGE_SELECTION_NAME` is being set to
    the basename of the entry point registering the extension.
    """

    """The version of the package selection extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    def add_arguments(self, *, parser):
        """
        Add command line arguments specific to the package selection.

        The method is intended to be overridden in a subclass.

        :param parser: The argument parser
        """
        pass

    def check_parameters(self, *, args, pkg_names):
        """
        Check is the passed arguments have valid values.

        The method is intended to be overridden in a subclass.
        It should either warn about invalid values and gracefully continue or
        raise a `SystemExit` exception.

        :param args: The parsed command line arguments
        :param pkg_names: The set of package names
        """
        pass

    def select_packages(self, *, args, decorators):
        """
        Identify the packages which should be skipped.

        By default all package decorators are marked as "selected".

        This method must be overridden in a subclass.

        :param args: The parsed command line arguments
        :param list decorators: The package decorators
        """
        raise NotImplementedError()


def add_arguments(parser):
    """
    Add the command line arguments for the package selection extensions.

    The function will call :function:`add_package_discovery_arguments` to add
    the package discovery arguments.

    :param parser: The argument parser
    """
    add_package_discovery_arguments(parser)

    _add_package_selection_arguments(parser)


def get_package_selection_extensions():
    """
    Get the available package selection extensions.

    The extensions are ordered by their entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.PACKAGE_SELECTION_NAME = name
    return order_extensions_by_name(extensions)


def _add_package_selection_arguments(parser):
    """
    Add the command line arguments for the package selection extensions.

    :param parser: The argument parser
    """
    package_selection_extensions = get_package_selection_extensions()
    group = parser.add_argument_group(title='Package selection arguments')
    for extension in package_selection_extensions.values():
        try:
            retval = extension.add_arguments(parser=group)
            assert retval is None, 'add_arguments() should return None'
        except Exception as e:
            # catch exceptions raised in package selection extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in package selection extension '
                "'{extension.PACKAGE_SELECTION_NAME}': {e}\n{exc}"
                .format_map(locals()))
            # skip failing extension, continue with next one


def get_packages(
    args, *,
    additional_argument_names=None,
    direct_categories=None, recursive_categories=None
):
    """
    Get the selected package decorators in topological order.

    The overview of the process:
    * Get the package descriptors
    * Order them topologically
    * Select the packages based on the command line arguments

    :param additional_argument_names: A list of additional arguments to
      consider
    :param Iterable[str] direct_categories: The names of the direct categories
    :param Iterable[str] recursive_categories: The names of the recursive
      categories
    :rtype: list
    :raises RuntimeError: if the returned set of packages contains duplicates
      package names
    """
    descriptors = get_package_descriptors(
        args, additional_argument_names=additional_argument_names)
    decorators = topological_order_packages(
        descriptors,
        direct_categories=direct_categories,
        recursive_categories=recursive_categories)
    select_package_decorators(args, decorators)

    pkgs = [m.descriptor for m in decorators if m.selected]
    if len({d.name for d in pkgs}) < len(pkgs):
        raise RuntimeError('Duplicate package names not supported')

    return decorators


def get_package_descriptors(args, *, additional_argument_names=None):
    """
    Get the package descriptors.

    The overview of the process:
    * Discover the package descriptors using the package discovery and
      identification extensions
    * Check is the passed package selection arguments have valid values
    * Augment the package descriptors

    :param additional_argument_names: A list of additional arguments to
      consider
    :returns: set of
      :py:class:`colcon_core.package_descriptor.PackageDescriptor`
    :rtype: set
    """
    extensions = get_package_identification_extensions()
    descriptors = discover_packages(args, extensions)

    pkg_names = {d.name for d in descriptors}
    _check_package_selection_parameters(args, pkg_names)

    augment_packages(
        descriptors, additional_argument_names=additional_argument_names)
    return descriptors


def _check_package_selection_parameters(args, pkg_names):
    package_selection_extensions = get_package_selection_extensions()
    for extension in package_selection_extensions.values():
        try:
            retval = extension.check_parameters(args=args, pkg_names=pkg_names)
            assert retval is None, 'check_parameters() should return None'
        except Exception as e:
            # catch exceptions raised in package selection extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in package selection extension '
                "'{extension.PACKAGE_SELECTION_NAME}': {e}\n{exc}"
                .format_map(locals()))
            # skip failing extension, continue with next one


def select_package_decorators(args, decorators):
    """
    Select the package decorators based on the command line arguments.

    The `selected` attribute of each decorator is updated by this function.

    :param args: The parsed command line arguments
    :param list decorators: The package decorators
    """
    # filtering must happen after the topological ordering since otherwise
    # packages in the middle of the dependency graph might be missing
    package_selection_extensions = get_package_selection_extensions()
    for extension in package_selection_extensions.values():
        try:
            retval = extension.select_packages(
                args=args, decorators=decorators)
            assert retval is None, 'select_packages() should return None'
        except Exception as e:
            # catch exceptions raised in package selection extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in package selection extension '
                "'{extension.PACKAGE_SELECTION_NAME}': {e}\n{exc}"
                .format_map(locals()))
            # skip failing extension, continue with next one
