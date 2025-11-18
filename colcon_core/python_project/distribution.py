# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from functools import lru_cache
from importlib.machinery import PathFinder
from importlib.util import cache_from_source
import os
from pathlib import Path
from pathlib import PurePosixPath
import sys

from colcon_core.python_install_path import get_python_install_path
from distlib.scripts import ScriptMaker

try:
    from importlib.metadata import Distribution
except ImportError:
    from importlib_metadata import Distribution


def _get_install_path(key, install_base):
    return get_python_install_path(key, {
        'base': str(install_base),
        'platbase': str(install_base),
    })


def _enumerate_files(path, _depth=1):
    if path.is_symlink() or path.is_file():
        yield PurePosixPath(*path.parts[-_depth:])
    elif path.is_dir():
        for child in path.iterdir():
            yield from _enumerate_files(child, _depth + 1)


def _find_prefix_path(metadata_path):
    # Walk the metadata path looking for either lib, Lib, or
    # sys.platlibdir. We can match that to determine our base directory.
    for i, part in enumerate(reversed(metadata_path.parent.parts), start=2):
        if part in ('lib', 'Lib', sys.platlibdir):
            return Path(*metadata_path.parts[:-i])


class PathLikeDistribution(Distribution):
    """
    A Python Distribution identified by a metadata path.

    This is similar to the private :class:`importlib.metadata.Distribution`
    implementation for :class:`importlib.metadata.PathDistribution`, but it
    exposes a property for the metadata path because that information is
    private to :class:`importlib.metadata.PathDistribution`.

    Because :class:`importlib.metadata.PathDistribution` is private and we
    don't really care what information provides the underlying implementation
    for representing the distribution, we call the public method
    :meth:`importlib.metadata.Distribution.at` to get an instance and then
    perform a sort of "cast" to this class type along with the path which was
    used to create the instance to begin with.
    """

    def __new__(cls, path, *args, **kwargs):
        """
        Create a new PathLikeDistribution object.

        :param path: The path to the distribution metadata directory

        :returns: A new object
        :rtype: PathLikeDistribution
        """
        res = Distribution.at(path)
        assert isinstance(res, Distribution)
        res.__class__ = cls._make_class(res.__class__)
        return res

    def __init__(self, path):
        """
        Construct a PathLikeDistribution.

        :param path: The path to the distribution metadata directory
        """
        self._metadata_path = Path(path)
        # NOTE: We do not call our super().__init__() because it was already
        # called as part of __new__().

    @classmethod
    @lru_cache
    def _make_class(cls, distribution_class):
        """
        Create a new dynamic subclass from PathLikeDistribution.

        :param distribution_class: The secondary class type to inherit from

        :returns: The new subclass type
        :rtype: Type
        """
        return type(
            '_Realized' + cls.__name__,
            (cls, distribution_class),
            {},
        )

    @staticmethod
    def at(path):  # noqa: D102
        return PathLikeDistribution(path)

    @property
    def path(self):
        """Get the path to the distribution metadata directory."""
        return self._metadata_path


class AllFilesDistribution(PathLikeDistribution):
    """
    A Python Distribution which enumerates all installed files.

    The typical :class:`importlib.metadata.Distribution` implementation only
    enumerates files which the distribution declares are a part of it, but
    there are circumstances which may lead to additional files being created
    during or after installation which are a part of the distribution but
    are not declared as such.
    """

    def __init__(self, path, *, prefix=None):
        """
        Construct a AllFilesDistribution.

        :param path: The path to the distribution metadata directory
        :param prefix: The path to the top-level installation prefix
        """
        super().__init__(path)
        self._prefix_path = prefix or _find_prefix_path(self.path)

    def _enumerate_top_level(self):
        top_level = (self.read_text('top_level.txt') or '').strip()
        if not top_level:
            return

        finder = PathFinder()
        path = (str(self.path.parent),)
        for module in (m.strip() for m in top_level.splitlines()):
            if not module:
                continue
            spec = finder.find_spec(module, path=path)
            if not spec or not spec.origin:
                continue
            origin = Path(spec.origin)
            if origin.name == '__init__.py':
                origin = origin.parent
            # Safety check, packages should always be a child of our
            # search directory.
            if origin.parent == self.path.parent:
                yield from _enumerate_files(origin)

    @classmethod
    @lru_cache
    def _get_script_maker(cls, script_dir):
        sm = ScriptMaker(None, script_dir, dry_run=True)
        sm.clobber = True
        sm.variants = {''}
        return sm

    def _enumerate_console_scripts(self):
        if not self.prefix:
            return
        entry_points = set(self.entry_points.select(group='console_scripts'))
        if not entry_points:
            return
        script_dir = _get_install_path('scripts', self.prefix)
        if not script_dir.is_dir():
            return
        script_maker = self._get_script_maker(script_dir)
        specs = [
            f'{script.name} = {script.value}'
            for script in entry_points
        ]
        for full_path in script_maker.make_multiple(specs):
            file = Path(full_path)
            if file.is_file():
                yield PurePosixPath(
                    file.relative_to(self.path.parent, walk_up=True))

    @staticmethod
    def at(path, *, prefix=None):  # noqa: D102
        return AllFilesDistribution(path, prefix=prefix)

    @property
    def prefix(self):
        """Get the prefix path to which the distribution is installed."""
        return self._prefix_path

    @property
    def all_files(self):
        """
        Superset of :py:attr:`files`, including additional undeclared files.

        Unlike :py:attr:`files`, this property will never be `None`.

        :returns: List of paths relative to the installation directory.
        :rtype: List[PurePosixPath]
        """
        files = set(self.files or ())

        # If there is no declarative file list at all, try to use
        # top_level.txt to remove the installed Python modules
        if not files:
            files.update(self._enumerate_top_level())

        # If the file list doesn't contain anything related to the metadata,
        # include all of the metadata we can find on disk
        metadata_path = PurePosixPath(self.path.name)
        if metadata_path not in files and not any(
            f.parent == metadata_path for f in files
        ):
            files.update(_enumerate_files(self.path))

        # Add any missing __pycache__ files
        py_files = tuple(f for f in files if f.suffix == '.py')
        for file in py_files:
            file_cache = PurePosixPath(cache_from_source(file))
            if file_cache in files:
                continue
            if not self.locate_file(file_cache).exists():
                continue
            files.add(file_cache)

        # Add any missing executables
        files.update(self._enumerate_console_scripts())

        return list(files)


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        target = os.getcwd()
    dist = AllFilesDistribution.at(target)
    for f in sorted(dist.all_files):
        print(f)
