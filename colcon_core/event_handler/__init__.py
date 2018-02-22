# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.plugin_system import get_first_line_doc
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_priority


class EventHandlerExtensionPoint:
    """
    The interface for event handler extensions.

    An event handler extension processes events.

    For each instance the attribute `EVENT_HANDLER_NAME` is being set to the
    basename of the entry point registering the extension.

    Custom event handlers don't need to be subclasses but only be callables
    accepting a single `event` argument.
    They are being registered as observers at an
    :py:class:`colcon_core.EventReactor` instance.
    The handler should check the type of the event and only act on known types.
    """

    """The version of the event handler extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of event handler extensions."""
    PRIORITY = 100

    def __init__(self):  # noqa: D107
        super().__init__()
        self.context = None
        self.enabled = True

    def __call__(self, event):
        """
        Process an event if the event type is known.

        This method must be overridden in a subclass.

        :param event: The event
        """
        raise NotImplementedError()


def get_event_handler_extensions(*, context):
    """
    Get the available event handler extensions.

    The extensions are ordered by their priority and entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.EVENT_HANDLER_NAME = name
        extension.context = context
    return order_extensions_by_priority(extensions)


def add_event_handler_arguments(parser):
    """
    Add the command line arguments for the event handler extensions.

    :param parser: The argument parser
    """
    group = parser.add_argument_group(title='Event handler arguments')
    extensions = get_event_handler_extensions(context=None)

    choices = []
    defaults = []
    descriptions = ''
    for key in sorted(extensions.keys()):
        # only offer the non-default choice
        choices.append(key + ('-' if extensions[key].enabled else '+'))
        defaults.append(key + ('+' if extensions[key].enabled else '-'))
        extension = extensions[key]
        desc = get_first_line_doc(extension)
        # ignore extensions without a description
        # since they are already listed in the defaults
        if desc:
            # it requires a custom formatter to maintain the newline
            descriptions += '\n* {key}: {desc}'.format_map(locals())

    group.add_argument(
        '--event-handlers',
        nargs='*', choices=choices, metavar=('name1+', 'name2-'),
        help='Enable (+) or disable (-) event handlers (default: %s)%s' %
             (' '.join(defaults), descriptions))


def apply_event_handler_arguments(extensions, args):
    """
    Enable/disable the event handler extensions based on the passed arguments.

    :param extensions: The event handler extensions
    :param args: The parsed command line arguments
    """
    for arg in (args.event_handlers or []):
        suffix = arg[-1]
        assert suffix in ('+', '-')
        key = arg[:-1]
        extension = extensions[key]
        extension.enabled = suffix == '+'
