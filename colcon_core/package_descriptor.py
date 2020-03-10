# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
from copy import deepcopy
import os
from pathlib import Path

from colcon_core.dependency_descriptor import DependencyDescriptor


class PackageDescriptor:
    """
    A descriptor for a package.

    A packages is identified by the following triplet:
    * the 'path' which must be an existing path
    * the 'type' which must be a non-empty string
    * the 'name' which must be a non-empty string

    Packages with the same type and name but different path are considered
    equal if their realpath is te same.

    'dependencies' are grouped by their category as `DependencyDescriptor` or
    `str`.

    Each item in 'hooks' must be a relative path in the installation space.

    The 'metadata' dictionary can store any additional information.
    """

    __slots__ = (
        'path',
        'type',
        'name',
        'dependencies',
        'hooks',
        'metadata',
    )

    def __init__(self, path):
        """
        Descriptor for a package in a specific path.

        :param str|Path path: The location of the package
        """
        self.path = Path(str(path))
        self.type = None
        self.name = None
        self.dependencies = defaultdict(set)
        # IDEA category specific hooks
        self.hooks = []
        self.metadata = {}

    def identifies_package(self):
        """
        Check if the package has a path, type and name.

        :returns: True if the descriptor has a path, type, and name
        :rtype: bool
        """
        return self.path and self.type and self.name

    def get_dependencies(self, *, categories=None):
        """
        Get the dependencies for specific categories or for all categories.

        :param Iterable[str] categories: The names of the specific categories
        :returns: The dependencies
        :rtype: set[DependencyDescriptor]
        :raises AssertionError: if the package name is listed as a dependency
        """
        dependencies = set()
        if categories is None:
            categories = self.dependencies.keys()
        for category in sorted(categories):
            dependencies |= self.dependencies[category]
        assert self.name not in dependencies, \
            "The package '{self.name}' has a dependency with the same name" \
            .format_map(locals())
        return {
            (DependencyDescriptor(d)
                if not isinstance(d, DependencyDescriptor) else d)
            for d in dependencies}

    def get_recursive_dependencies(
        self, descriptors, direct_categories=None, recursive_categories=None,
    ):
        """
        Get the recursive dependencies.

        Dependencies which are not in the set of package descriptor names are
        ignored.

        :param set descriptors: The known packages to
          consider
        :param Iterable[str] direct_categories: The names of the direct
          categories
        :param Iterable[str] recursive_categories: The names of the recursive
          categories
        :returns: The dependencies
        :rtype: set[DependencyDescriptor]
        :raises AssertionError: if a package lists itself as a dependency
        """
        # the following variable only exists for faster access within the loop
        descriptors_by_name = defaultdict(set)
        for d in descriptors:
            descriptors_by_name[d.name].add(d)
        queue = self.get_dependencies(categories=direct_categories)
        dependencies = set()
        depth = 0
        while queue:
            # ignore redundant dependencies
            level_queue = queue - dependencies
            queue.clear()
            depth += 1
            for dep in level_queue:
                # ignore circular dependencies
                if dep == self.name:
                    continue
                # ignore unknown dependencies
                # explicitly allow multiple packages with the same name
                descs = descriptors_by_name[dep]
                if not descs:
                    continue
                # recursing into the same function of the dependency descriptor
                # queue recursive dependencies
                for d in descs:
                    queue |= d.get_dependencies(
                        categories=recursive_categories)
                # duplicate the descriptor and metadata and add the depth
                dep = deepcopy(dep)
                dep.metadata['depth'] = depth
                # add dependency to result set
                dependencies.add(dep)
        return dependencies

    def __hash__(self):  # noqa: D105
        # the hash doesn't include the path since different paths are
        # considered equal if their realpath is the same
        return hash((self.type, self.name))

    def __eq__(self, other):  # noqa: D105
        if type(self) != type(other):
            return NotImplemented
        if (self.type, self.name) != (other.type, other.name):
            return False
        if self.path == other.path:
            return True
        # check realpath last since it is the most expensive to compute
        return os.path.realpath(str(self.path)) == \
            os.path.realpath(str(other.path))

    def __str__(self):  # noqa: D105
        return '{' + ', '.join(
            ['%s: %s' % (s, getattr(self, s)) for s in self.__slots__]) + '}'
