# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import traceback

from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_priority
from colcon_core.python_project.hook_caller import get_hook_caller

logger = colcon_logger.getChild(__name__)


class HookCallerDecoratorExtensionPoint:
    """
    The interface for PEP 517 hook caller decorator extensions.

    For each instance the attribute `HOOK_CALLER_DECORATOR_NAME` is being
    set to the basename of the entry point registering the extension.
    """

    """The version of the hook caller decorator extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of hook caller decorator extensions."""
    PRIORITY = 100

    def decorate_hook_caller(self, *, hook_caller):
        """
        Decorate a hook caller to perform additional functionality.

        This method must be overridden in a subclass.

        :param hook_caller: The hook caller
        :returns: A decorator
        """
        raise NotImplementedError()


def get_hook_caller_extensions():
    """
    Get the available hook caller decorator extensions.

    The extensions are ordered by their priority and entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.HOOK_CALLER_DECORATOR_NAME = name
    return order_extensions_by_priority(extensions)


def decorate_hook_caller(hook_caller):
    """
    Decorate the hook caller using hook caller decorator extensions.

    :param hook_caller: The hook caller

    :returns: The decorated parser
    """
    extensions = get_hook_caller_extensions()
    for extension in extensions.values():
        logger.log(
            1, 'decorate_hook_caller() %s',
            extension.HOOK_CALLER_DECORATOR_NAME)
        try:
            decorated_hook_caller = extension.decorate_hook_caller(
                hook_caller=hook_caller)
            assert hasattr(decorated_hook_caller, 'call_hook'), \
                'decorate_hook_caller() should return something to call hooks'
        except Exception as e:  # noqa: F841
            # catch exceptions raised in decorator extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in hook caller decorator extension '
                f"'{extension.HOOK_CALLER_DECORATOR_NAME}': {e}\n{exc}")
            # skip failing extension, continue with next one
        else:
            hook_caller = decorated_hook_caller

    return hook_caller


def get_decorated_hook_caller(desc, **kwargs):
    """
    Create and decorate a hook caller instance for a package descriptor.

    :param desc: The package descriptor
    """
    hook_caller = get_hook_caller(desc, **kwargs)
    decorated_hook_caller = decorate_hook_caller(hook_caller)
    return decorated_hook_caller
