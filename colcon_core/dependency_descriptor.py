# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0


class DependencyDescriptor(str):
    """
    A descriptor for a package dependency.

    A dependency is identified by its name. This subclasses str for backwards
    compatibility purposes.

    The 'metadata' dictionary can store any additional information.
    """

    __slots__ = (
        '_name',
        'metadata'
    )

    def __new__(cls, name, metadata=None):
        """
        Descriptor for a package dependency.

        :param str value: Name of the declared dependency
        :param dict metadata: Any metadata associated with
        the dependency
        """
        name_copy = str(name)
        obj = str.__new__(cls, name_copy)
        return obj

    def __init__(self, name, metadata=None):  # noqa: D107
        super(DependencyDescriptor, self).__init__()
        self._name = name
        self.metadata = metadata if metadata is not None else {}

    @property
    def name(self):
        """Name of the dependency."""
        return self._name

    def __eq__(self, other):  # noqa: D105
        if isinstance(other, DependencyDescriptor):
            return self._name == other._name and \
                self.metadata == other.metadata
        else:
            return self._name == other

    def __hash__(self):  # noqa: D105
        return hash(self._name)


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
