# Copyright 2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import copy


class DependencyDescriptor(str):
    """
    A descriptor for a package dependency.

    Beside the name of the dependency the 'metadata' dictionary can store any
    additional information.

    A dependency is identified by its name.
    The 'metadata' dictionary can store any additional information.

    Currently the class is inheriting from str for backwards compatibility.
    You should not rely on this but use the `name` property instead.
    """

    @staticmethod
    def __new__(cls, name, *args, **kwargs):  # noqa: D102
        return str.__new__(cls, name)

    def __init__(  # noqa: D107
        self, name, *, metadata=None, package_name=None,
    ):
        self.metadata = metadata if metadata is not None else {}
        self._package_name = package_name or self.name

    @property
    def name(self):
        """
        Name of the dependency.

        The property exists for future compatibility when the base class is
        removed.

        :rtype: str
        """
        return str(self)

    @property
    def package_name(self):
        """
        Name of the package which provides the dependency.

        :rtype: str
        """
        return self._package_name

    def __deepcopy__(self, memo=None):  # noqa: D105
        # surprisingly this is significantly faster than the default
        if not self.metadata:
            # explicitly skipping the deep copy of an empty dict is also faster
            return DependencyDescriptor(self.name)
        return DependencyDescriptor(
            self.name, metadata=copy.deepcopy(self.metadata, memo=memo))
