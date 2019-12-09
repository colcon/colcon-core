# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import OrderedDict

from colcon_core.argument_parser import ArgumentParserDecorator


class DestinationCollectorDecorator(ArgumentParserDecorator):
    """Collect the option names and destination of arguments."""

    def __init__(self, parser, **kwargs):
        """
        Construct a DestinationCollectorDecorator.

        :param parser: The argument parser to decorate
        """
        # avoid setting members directly, the base class overrides __setattr__
        # pass them as keyword arguments instead
        super().__init__(
            parser,
            _destinations=OrderedDict(),
            **kwargs)

    def get_destinations(self):
        """
        Get destinations for all added arguments.

        :returns: The destination names
        :rtype: OrderedDict
        """
        destinations = OrderedDict()
        destinations.update(self._destinations)
        for d in self._nested_decorators:
            destinations.update(d.get_destinations())
        return destinations

    def add_argument(self, *args, **kwargs):
        """Collect option names and destination for all added arguments."""
        argument = self._parser.add_argument(*args, **kwargs)

        for arg in args:
            if not arg.startswith('-'):
                continue
            key = arg.lstrip('-')
            assert key not in self._destinations
            self._destinations[key] = argument.dest

        return argument
