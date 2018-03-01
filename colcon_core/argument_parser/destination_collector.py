# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.argument_parser import ArgumentParserDecorator


class DestinationCollectorDecorator(ArgumentParserDecorator):
    """Collect destinations of arguments."""

    def __init__(self, parser):
        """
        Constructor.

        :param parser: The argument parser to decorate
        """
        # avoid setting members directly, the base class overrides __setattr__
        # pass them as keyword arguments instead
        super().__init__(
            parser,
            _destinations=[])

    def get_destinations(self):
        """
        Get destinations for all added arguments.

        :returns: The destination names
        :rtype: list
        """
        destinations = []
        destinations += self._destinations
        for d in self._nested_decorators:
            destinations += d.get_destinations()
        return destinations

    def add_argument(self, *args, **kwargs):
        """Collect destinations for all added arguments."""
        argument = self._parser.add_argument(*args, **kwargs)

        self._destinations.append(argument.dest)

        return argument
