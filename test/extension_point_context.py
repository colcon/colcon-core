# Copyright 2016-2018 Dirk Thomas
# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from colcon_core import plugin_system


class ExtensionPointContext:

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._memento = None

    def __enter__(self):
        # reset entry point cache, provide new instances in each scope
        plugin_system._extension_instances.clear()

        self._memento = plugin_system.load_extension_points

        def load_extension_points(_, *, excludes=None):
            nonlocal self
            return {
                k: v for k, v in self._kwargs.items()
                if excludes is None or k not in excludes}

        plugin_system.load_extension_points = load_extension_points

    def __exit__(self, *_):
        plugin_system.load_extension_points = self._memento
