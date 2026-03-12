# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from functools import lru_cache
from importlib.machinery import PathFinder
from importlib.util import cache_from_source
import itertools
import os
from pathlib import Path
from pathlib import PurePosixPath
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


def _find_prefix_path(metadata_path):
    # Walk the metadata path looking for either lib, Lib, or
    # sys.platlibdir. We can match that to determine our base directory.
    # NOTE: sys.platlibdir was introduced in Python 3.9.
    for i, part in enumerate(reversed(metadata_path.parent.parts), start=2):
        if part in ('lib', 'Lib', getattr(sys, 'platlibdir', 'lib64')):
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

    @classmethod
    def discover(cls, *, context=None, **kwargs):  # noqa: D102
        if context and kwargs:
            raise ValueError('cannot accept context and kwargs')
        context = context or DistributionFinder.Context(**kwargs)
        return itertools.chain.from_iterable(
            cls.survey(child)
            for path in context.path
            for child in Path(path).iterdir()
        )

    @classmethod
    def survey(cls, path, *args, **kwargs):
        """
        Survey a path for any compatible distribution metadata.

        Remaining arguments to this function are passed to the ``at`` function
        during for any created distribution instances.

        :param path: Candidate path to consider.
        """
        if path.suffix.lower() in ('.dist-info', '.egg-info'):
            yield cls.at(path, *args, **kwargs)

    @property
    def name(self):
        """
        Return the 'Name' metadata for the distribution package.

        This property can can be dropped when the minimum Python version is
        bumped to at least Python 3.10, where it was added to the
        ``Distribution`` class.
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

    def __init__(self, path, *, _link_path=None):
        """
        Construct a InstalledDistribution.

        :param path: The path to the distribution metadata directory
        :param _link_path: The path to file which linked to this distribution
          during discovery, if any
        """
        super().__init__(path)
        self._link_path = _link_path

    @staticmethod
    def at(path, *, _link_path=None):  # noqa: D102
        return InstalledDistribution(path, _link_path=_link_path)

    @classmethod
    def survey(cls, path, *args, **kwargs):  # noqa: D102
        if path.is_file() and path.suffix.lower() == '.egg-link':
            egg_link = [line for line in path.read_text().splitlines() if line]
            search_dir = (path.parent / egg_link[0]).resolve()
            tgt = super().survey
            yield from itertools.chain.from_iterable(
                tgt(child, *args, _link_path=path, **kwargs)
                for child in search_dir.iterdir()
            )
        else:
            yield from super().survey(path, *args, **kwargs)

    @property
    def files(self):  # noqa: D102
        if not self._link_path:
            return super().files

    @property
    def path(self):  # noqa: D102
        return self._link_path or super().path

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
        prefix_path = _find_prefix_path(self.path)
        if not prefix_path:
            return
        entry_points = {
            ep for ep in self.entry_points
            if ep.group == 'console_scripts'
        }
        if not entry_points:
            return
        script_dir = _get_install_path('scripts', prefix_path)
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

        # Add any missing executables
        files.update(self._enumerate_console_scripts())

        # Add any missing __pycache__ files
        py_files = tuple(f for f in files if f.suffix == '.py')
        for file in py_files:
            file_cache = PurePosixPath(Path(cache_from_source(file)))
            if file_cache in files:
                continue
            if not self.locate_file(file_cache).exists():
                continue
            files.add(file_cache)

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
