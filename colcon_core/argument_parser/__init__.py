# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import traceback

from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_priority

logger = colcon_logger.getChild(__name__)


class ArgumentParserDecoratorExtensionPoint:
    """
    The interface for argument parser decorator extensions.

    An argument parser decorator extension performs additional functionality
    when adding command line arguments.

    For each instance the attribute `ARGUMENT_PARSER_DECORATOR_NAME` is being
    set to the basename of the entry point registering the extension.
    """

    """The version of the argument parser decorator extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of argument parser decorator extensions."""
    PRIORITY = 100

    def decorate_argument_parser(self, *, parser):
        """
        Decorate an argument parser to perform additional functionality.

        This method must be overridden in a subclass.

        :param parser: The argument parser
        :returns: A decorator
        """
        raise NotImplementedError()


def get_argument_parser_extensions():
    """
    Get the available argument parser extensions.

    The extensions are ordered by their priority and entry point name.

    :rtype: OrderedDict
    """
    extensions = instantiate_extensions(__name__)
    for name, extension in extensions.items():
        extension.ARGUMENT_PARSER_DECORATOR_NAME = name
    return order_extensions_by_priority(extensions)


def decorate_argument_parser(parser):
    """
    Decorate the parser using the available argument parser extensions.

    :param parser: The argument parser
    :returns: The decorated parser
    """
    extensions = get_argument_parser_extensions()
    for extension in extensions.values():
        logger.log(
            1, 'decorate_argument_parser() %s',
            extension.ARGUMENT_PARSER_DECORATOR_NAME)
        try:
            decorated_parser = extension.decorate_argument_parser(
                parser=parser)
            assert hasattr(decorated_parser, 'add_argument'), \
                'decorate_argument_parser() should return a parser like object'
        except Exception as e:
            # catch exceptions raised in decorator extension
            exc = traceback.format_exc()
            logger.error(
                'Exception in argument parser decorator extension '
                "'{extension.ARGUMENT_PARSER_DECORATOR_NAME}': {e}\n{exc}"
                .format_map(locals()))
            # skip failing extension, continue with next one
        else:
            parser = decorated_parser

    return parser


class ArgumentParserDecorator:
    """
    Decorate an argument parser as well as all recursive subparsers.

    The methods and arguments are the same as :class:`argparse.ArgumentParser`.

    Subclasses can perform any kind of task when e.g. arguments are being added
    without being concerned in which part of the hierarchy it is added.

    Subclasses should not set any member variables directly but pass them as
    keyword arguments to the constructor.
    """

    def __init__(self, parser, **kwargs):
        """
        Decorate an argument parser.

        :param parser: The argument parser to decorate
        :param **kwargs: The keyword arguments are set as attributes on this
          instance
        """
        assert '_parser' not in kwargs
        kwargs['_parser'] = parser
        assert '_nested_decorators' not in kwargs
        kwargs['_nested_decorators'] = []
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def __getattr__(self, name):
        """
        Get an attribute from this decorator if it exists or the decoree.

        :param str name: The name of the attribute
        :returns: The attribute value
        :raises AttributeError: if the attribute doesn't exist in either of the
          two instances
        """
        # when argcomplete changes self.__class__ at runtime
        # the instance might not have a _parser attribute anymore
        if '_parser' not in self.__dict__:
            raise AttributeError(name)
        # get attribute from decoree
        return getattr(self.__dict__['_parser'], name)

    def __setattr__(self, name, value):
        """
        Set an attribute value on this decorator if it exists or the decoree.

        :param str name: The name of the attribute
        :param value: The attribute value
        """
        # overwrite existing attribute
        if name in self.__dict__:
            self.__dict__[name] = value
            return
        # when argcomplete changes self.__class__ at runtime
        # the instance might not have a _parser attribute anymore
        if '_parser' not in self.__dict__:
            self.__dict__[name] = value
            return
        # get attribute on decoree
        setattr(self.__dict__['_parser'], name, value)

    def add_argument_group(self, *args, **kwargs):
        """
        Decorate group parser before adding.

        See :class:`argparse.ArgumentParser.add_argument_group` for the method
        arguments and return value.
        """
        group = self.__class__(
            self._parser.add_argument_group(*args, **kwargs))
        self._nested_decorators.append(group)
        return group

    def add_mutually_exclusive_group(self, *args, **kwargs):
        """
        Decorate mutually exclusive group parser before adding.

        See :class:`argparse.ArgumentParser.add_mutually_exclusive_group` for
        the method arguments and return value.
        """
        group = self.__class__(
            self._parser.add_mutually_exclusive_group(*args, **kwargs))
        self._nested_decorators.append(group)
        return group

    def add_parser(self, *args, **kwargs):
        """
        Decorate parser before adding.

        See :class:`argparse.ArgumentParser.add_parser` for the method
        arguments and return value.
        """
        parser = self.__class__(
            self._parser.add_parser(*args, **kwargs))
        self._nested_decorators.append(parser)
        return parser

    def add_subparsers(self, *args, **kwargs):
        """
        Decorate subparser before adding.

        See :class:`argparse.ArgumentParser.add_subparsers` for the method
        arguments and return value.
        """
        subparser = self.__class__(
            self._parser.add_subparsers(*args, **kwargs))
        self._nested_decorators.append(subparser)
        return subparser
