# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import OrderedDict

from colcon_core.package_decorator import PackageDecorator


def topological_order_packages(
    descriptors, direct_categories=None, recursive_categories=None,
):
    """
    Order packages topologically.

    :param descriptors: the package descriptors
    :type descriptors: set of
      :py:class:`colcon_core.package_descriptor.PackageDescriptor`

    :returns: list of package decorators
    :rtype: list of :py:class:`colcon_core.package_decorator.PackageDecorator`
    """
    # get recursive dependencies for all packages
    queued = set()
    for descriptor in descriptors:
        rec_deps = descriptor.get_recursive_dependencies(
            descriptors,
            direct_categories=direct_categories,
            recursive_categories=recursive_categories)
        d = _PackageDependencies(
            descriptor=descriptor,
            recursive_dependencies=rec_deps,
            remaining_dependencies={d.name for d in rec_deps},
        )
        queued.add(d)

    ordered = OrderedDict()
    while len(ordered) < len(descriptors):
        # remove dependencies on already ordered packages
        ordered_names = {descriptor.name for descriptor in ordered.keys()}
        for q in queued:
            q.remaining_dependencies -= ordered_names

        # find all queued packages without remaining dependencies
        ready = list(filter(lambda q: not q.remaining_dependencies, queued))
        if not ready:
            lines = [
                '%s: %s' % (
                    q.descriptor.name, sorted(q.remaining_dependencies))
                for q in queued]
            lines.sort()
            raise RuntimeError(
                'Unable to order packages topologically:\n' + '\n'.join(lines))

        # order ready jobs alphabetically for a deterministic order
        ready.sort(key=lambda d: d.descriptor.name)

        # add all ready jobs to ordered dictionary
        for r in ready:
            ordered[r.descriptor] = r.recursive_dependencies
            queued.remove(r)

    # create ordered list of package decorators
    decorators = []
    ordered_keys = [descriptor.name for descriptor in ordered.keys()]
    for descriptor, recursive_dependencies in ordered.items():
        decorator = PackageDecorator(descriptor)
        # reorder recursive dependencies according to the topological ordering
        decorator.recursive_dependencies = sorted(
            (d for d in recursive_dependencies if d in ordered_keys),
            key=ordered_keys.index)
        decorators.append(decorator)

    return decorators


class _PackageDependencies:

    __slots__ = (
        'descriptor', 'recursive_dependencies', 'remaining_dependencies')

    def __init__(
        self, descriptor, recursive_dependencies, remaining_dependencies,
    ):
        self.descriptor = descriptor
        self.recursive_dependencies = recursive_dependencies
        self.remaining_dependencies = remaining_dependencies
