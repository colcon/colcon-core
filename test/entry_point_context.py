# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core import plugin_system


class EntryPointContext:

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._memento = None

    def __enter__(self):
        # reset entry point cache, provide new instances in each scope
        plugin_system._extension_instances.clear()

        self._memento = plugin_system.load_entry_points

        def load_entry_points(_, *, exclude_names=None):
            nonlocal self
            return {
                k: v for k, v in self._kwargs.items()
                if exclude_names is None or k not in exclude_names}

        plugin_system.load_entry_points = load_entry_points

    def __exit__(self, *_):
        plugin_system.load_entry_points = self._memento
