# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from functools import lru_cache
import importlib.machinery
from importlib.util import cache_from_source
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import sys

from colcon_core.python_install_path import get_python_install_path
from distlib.scripts import ScriptMaker

try:
    from importlib.metadata import Distribution
    from importlib.metadata import DistributionFinder
except ImportError:
    from importlib_metadata import Distribution
    from importlib_metadata import DistributionFinder


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


class PathLikeDistribution(Distribution):
    """
    A Python Distribution identified by a metadata path.

    This class wraps a :class:`importlib.metadata.Distribution` instance
    obtained via :meth:`importlib.metadata.Distribution.at`.

    Composition is used here instead of inheritance or dynamic class mutation
    (like ``__class__`` assignment) to ensure compatibility with all
    implementations of the ``Distribution`` ABC, including those which might
    be implemented in C or use ``__slots__``, which would prevent dynamic
    subclassing or class reassignment.
    """

    def __init__(self, path):
        """
        Construct a PathLikeDistribution.

        :param path: The path to the distribution metadata directory
        """
        self._metadata_path = Path(path)
        self._dist = Distribution.at(path)

    def read_text(self, filename):  # noqa: D102
        return self._dist.read_text(filename)

    def locate_file(self, path):  # noqa: D102
        return self._dist.locate_file(path)

    @staticmethod
    def at(path):  # noqa: D102
        return PathLikeDistribution(path)

    @classmethod
    def discover(cls, *, context=None, **kwargs):  # noqa: D102
        if context and kwargs:
            raise ValueError('cannot accept context and kwargs')
        context = context or DistributionFinder.Context(**kwargs)
        for path in (Path(p) for p in context.path):
            if not path.is_dir():
                continue
            try:
                for child in path.iterdir():
                    yield from cls.survey(child)
            except OSError:
                continue

    @classmethod
    def survey(cls, path):
        """
        Survey a path for any compatible distribution metadata.

        :param path: Candidate path to consider.
        """
        if path.suffix.lower() in ('.dist-info', '.egg-info'):
            yield cls.at(path)

    @property
    def name(self):
        """
        Return the 'Name' metadata for the distribution package.

        This property can be dropped when the minimum Python version is bumped
        to at least Python 3.10, where it was added to the ``Distribution``
        class.
        """
        return self.metadata['Name']

    @property
    def path(self):
        """Get the path to the distribution metadata directory."""
        return self._metadata_path


class InstalledDistribution(PathLikeDistribution):
    """
    A Python Distribution which enumerates all installed files.

    The typical :class:`importlib.metadata.Distribution` implementation only
    enumerates files which the distribution declares are a part of it, but
    there are circumstances which may lead to additional files being created
    during or after installation which are a part of the distribution but
    are not declared as such.
    """

    def __init__(self, path):
        """
        Construct a InstalledDistribution.

        :param path: The path to the distribution metadata directory
        """
        super().__init__(path)
        self._link_path = None
        self._prefix_path = None

    @staticmethod
    def at(path, *, prefix_path=None):  # noqa: D102
        dist = InstalledDistribution(path)
        dist._prefix_path = Path(prefix_path) if prefix_path else None
        return dist

    @classmethod
    def discover(  # noqa: D102
        cls, *, context=None, prefix_path=None, **kwargs
    ):
        for dist in super().discover(context=context, **kwargs):
            dist._prefix_path = Path(prefix_path) if prefix_path else None
            yield dist

    @classmethod
    def survey(cls, path, *args, prefix_path=None, **kwargs):  # noqa: D102
        prefix_path = Path(prefix_path) if prefix_path else None
        if path.is_file() and path.suffix.lower() == '.egg-link':
            egg_link = next((
                line for line in path.read_text().splitlines() if line), None)
            if not egg_link:
                return
            search_dir = (path.parent / egg_link).resolve()
            if not search_dir.is_dir():
                return
            for child in search_dir.iterdir():
                for dist in super().survey(child):
                    dist._link_path = path
                    dist._prefix_path = prefix_path
                    yield dist
        else:
            for dist in super().survey(path):
                dist._prefix_path = prefix_path
                yield dist

    @property
    def files(self):  # noqa: D102
        if not self._link_path:
            return super().files

    @property
    def path(self):  # noqa: D102
        return self._link_path or super().path

    def _enumerate_top_level(self):
        top_level = {
            name.strip() for name in
            (self.read_text('top_level.txt') or '').splitlines()
        }
        if not top_level:
            return

        namespaces = {
            name.strip() for name in
            (self.read_text('namespace_packages.txt') or '').splitlines()
        }
        base_path = self.path.parent
        suffixes = tuple(importlib.machinery.all_suffixes())

        for module in top_level - namespaces:
            if not module:
                continue

            module_path = base_path / module

            # Check if it's a package directory
            if module_path.is_dir():
                yield from _enumerate_files(module_path)
                continue

            # Check if it's a single-file module (including extensions)
            for module_file in map(module_path.with_suffix, suffixes):
                if module_file.is_file():
                    yield from _enumerate_files(module_file)

    @classmethod
    @lru_cache(maxsize=32)
    def _get_script_maker(cls, script_dir):
        sm = ScriptMaker(None, script_dir, dry_run=True)
        sm.clobber = True
        sm.variants = {''}
        return sm

    def _enumerate_console_scripts(self):
        if not self._prefix_path:
            return
        entry_points = {
            ep for ep in self.entry_points
            if ep.group == 'console_scripts'
        }
        if not entry_points:
            return
        script_dir = _get_install_path('scripts', self._prefix_path)
        if not script_dir.is_dir():
            return

        script_paths = set()

        script_names = {ep.name for ep in entry_points}
        pattern = re.compile(
            r'^(' + '|'.join(map(re.escape, script_names)) + r')'
            r'(?:-\d+\.\d+|-script\.pyw?|\.exe(?:\.manifest)?|\.bat|\.cmd)?$'
        )

        script_paths.update(
            f for f in script_dir.iterdir()
            if f.is_file() and pattern.match(f.name)
        )

        script_maker = self._get_script_maker(str(script_dir))
        specs = [
            f'{script.name} = {script.value}'
            for script in entry_points
        ]
        for full_path in script_maker.make_multiple(specs):
            file = Path(full_path)
            if file.is_file():
                script_paths.add(file)

        for file in script_paths:
            file_relative = os.path.relpath(
                str(file), start=str(self.path.parent))
            yield PurePosixPath(Path(file_relative))

    def get_installed_files(self):
        """
        Superset of :py:attr:`files`, including additional undeclared files.

        Unlike :py:attr:`files`, this property will never be `None`.

        :returns: List of paths relative to the installation directory.
        :rtype: List[PurePosixPath]
        """
        files = {
            PurePosixPath(Path(file)) for file in self.files or ()
            if self.locate_file(file).exists()
        }

        # If there is no declarative file list at all, try to use
        # top_level.txt to recover the installed Python modules
        if not files:
            files.update(self._enumerate_top_level())

        # If the file list doesn't contain anything related to the metadata,
        # include all of the metadata we can find on disk
        metadata_path = PurePosixPath(self.path.name)
        if metadata_path not in files and not any(
            f.parent == metadata_path for f in files
        ):
            files.update(_enumerate_files(self.path))

        # Add any missing executables
        files.update(self._enumerate_console_scripts())

        # Add any missing __pycache__ files
        py_files = tuple(f for f in files if f.suffix == '.py')
        for file in py_files:
            file_cache = Path(cache_from_source(file))
            cache_dir = file_cache.parent
            abs_cache_dir = self.locate_file(cache_dir)
            if not abs_cache_dir.is_dir():
                continue
            for cache_file in abs_cache_dir.glob(f'{file_cache.stem}*.pyc'):
                rel_cache = PurePosixPath(cache_dir / cache_file.name)
                files.add(rel_cache)

        return list(files)


if __name__ == '__main__':
    try:
        target = sys.argv[1]
    except IndexError:
        target = os.getcwd()
    for dist in InstalledDistribution.discover(path=[target]):
        print(f'# {dist.name}@{dist.version}')
        for f in sorted(dist.get_installed_files()):
            print(f)
