# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import namedtuple
from collections import OrderedDict
import sys


EnvironmentVariable = namedtuple(
    'EnvironmentVariable', ('name', 'description'))

if sys.platform == 'win32':

    class EnvironDict(OrderedDict):
        """
        A case-insensitive dictionary for environment variables.

        This class has to work pretty hard to inherit from
        :class:`collections.OrderedDict`. In the future, it might be better to
        document and enforce function return values as implementing
        :class:`collections.abc.Mapping` rather than actual :class:`dict`
        instances.
        """

        def __init__(self, data=None, **kwargs):
            """Initialize the dictionary."""
            self._casing = {}
            super().__init__()
            if data is None:
                data = {}
            self.update(data, **kwargs)

        def __setitem__(self, key, value):
            """Set value for a key, preserving its original casing."""
            upper_key = key.upper()
            if upper_key in self._casing:
                key = self._casing[upper_key]
            else:
                self._casing[upper_key] = key
            super().__setitem__(key, value)

        def __getitem__(self, key):
            """Get the value for a key."""
            upper_key = key.upper()
            if upper_key in self._casing:
                orig_key = self._casing[upper_key]
                try:
                    return super().__getitem__(orig_key)
                except KeyError:
                    del self._casing[upper_key]
            raise KeyError(key)

        def __delitem__(self, key):
            """Delete a key."""
            upper_key = key.upper()
            if upper_key in self._casing:
                orig_key = self._casing.pop(upper_key)
                try:
                    super().__delitem__(orig_key)
                except KeyError:
                    raise KeyError(key)
            else:
                raise KeyError(key)

        def __contains__(self, key):
            """Check if a key exists."""
            if not isinstance(key, str):
                return False
            return key.upper() in self._casing

        def get(self, key, default=None):
            """Get the value for a key or a default."""
            if not isinstance(key, str):
                return default
            upper_key = key.upper()
            if upper_key in self._casing:
                orig_key = self._casing[upper_key]
                try:
                    return super().__getitem__(orig_key)
                except KeyError:
                    del self._casing[upper_key]
            return default

        def pop(self, key, *args):
            """Remove a key and return its value."""
            upper_key = key.upper()
            if upper_key in self._casing:
                orig_key = self._casing.pop(upper_key)
                try:
                    return super().pop(orig_key)
                except KeyError:
                    pass
            if args:
                return args[0]
            raise KeyError(key)

        def popitem(self, last=True):
            """Remove and return a (key, value) pair from the dictionary."""
            key, value = super().popitem(last)
            self._casing.pop(key.upper(), None)
            return key, value

        def setdefault(self, key, default=None):
            """Set default value for a key."""
            upper_key = key.upper()
            if upper_key in self._casing:
                return super().setdefault(self._casing[upper_key], default)
            self._casing[upper_key] = key
            return super().setdefault(key, default)

        def update(self, data=None, **kwargs):
            """Update the dictionary with items from another mapping."""
            if data is not None:
                if hasattr(data, 'keys'):
                    for k in data.keys():
                        self[k] = data[k]
                else:
                    for k, v in data:
                        self[k] = v
            for k, v in kwargs.items():
                self[k] = v

        def clear(self):
            """Clear the dictionary."""
            self._casing.clear()
            super().clear()

        def upper_items(self):
            """Like iteritems(), but with all uppercase keys."""
            return (
                (k.upper(), v)
                for k, v in self.items()
            )

        def copy(self):
            """Return a shallow copy of the dictionary."""
            return EnvironDict(self)

        def __eq__(self, other):
            """Compare to another mapping case-insensitively."""
            from collections.abc import Mapping
            if isinstance(other, Mapping):
                other = EnvironDict(other)
            else:
                return NotImplemented
            # Compare insensitively
            return dict(self.upper_items()) == dict(other.upper_items())

        def __repr__(self):
            """Return the string representation."""
            return str(dict(self.items()))
else:
    EnvironDict = OrderedDict
