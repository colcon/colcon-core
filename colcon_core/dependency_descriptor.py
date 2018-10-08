# Copyright 2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import collections


class DependencyDescriptor(collections.UserString):
    """
    A descriptor for a package dependency.

    Beside the name of the dependency the 'metadata' dictionary can store any
    additional information.

    A dependency is identified by its name.
    The 'metadata' dictionary can store any additional information.

    Currently the class is inheriting from str for backwards compatibility.
    You should not rely on this but use the `name` property instead.
    """

    def __init__(self, *args, metadata=None, **kwargs):  # noqa: D107
        super().__init__(*args, **kwargs)
        self.metadata = metadata if metadata is not None else {}

    @property
    def name(self):
        """
        Name of the dependency.

        The property exists for future compatibility when the base class is
        removed.

        :rtype: str
        """
        return str(self)
