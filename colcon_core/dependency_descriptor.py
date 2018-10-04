# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0


class DependencyDescriptor:
    """
    A descriptor for a package dependency.

    A dependency is identified by its name.

    The 'metadata' dictionary can store any additional information.
    """

    __slots__ = (
        '_name',
        'metadata'
    )

    def __init__(self, name, *, metadata=None):
        """
        Descriptor for a package dependency.

        :param str name: Name of the declared dependency
        :param dict metadata: Any metadata associated with
        the dependency
        """
        self._name = name
        self.metadata = metadata if metadata is not None else {}

    @property
    def name(self):
        """Name of the dependency."""
        return self._name

    def __str__(self):  # noqa: D105
        return '{' + ', '.join(
            ['%s: %s' % (s, getattr(self, s)) for s in self.__slots__]) + '}'


def dependency_name(dependency):
    """
    Get the name of the dependency.

    This should be used to maintain backwards compatibility with extensions
    that treat PackageDescriptor.dependencies as a list of strings
    instead of a list of DependencyDescriptor

    :param dependency: string or DependencyDescriptor
    :return: name of the dependency
    :rtype: str
    """
    if isinstance(dependency, DependencyDescriptor):
        return dependency.name
    elif isinstance(dependency, str):
        return dependency
    else:
        raise RuntimeError(
            'Passed in object is not a str or DependencyDescriptor')
