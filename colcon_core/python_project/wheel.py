# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Uninstallation and cleanup utilities for Python packages."""

import os
from pathlib import Path

from colcon_core.logging import colcon_logger
from colcon_core.python_project.distribution import _get_install_path
from colcon_core.python_project.distribution import InstalledDistribution

logger = colcon_logger.getChild(__name__)


def remove_distributions(name, install_base):
    """
    Remove any installed distributions with the given name.

    :param str name: Name of the distribution
    :param Path install_base: Path to the base directory to uninstall from
    """
    install_base = Path(install_base)
    libdirs = [
        Path(_get_install_path('purelib', install_base)),
        Path(_get_install_path('platlib', install_base)),
    ]

    dists = list(
        InstalledDistribution.discover(
            name=name,
            path=[str(d) for d in libdirs],
            prefix_path=install_base,
        )
    )
    # InstalledDistribution.discover yields all distributions found on
    # the path; filter for the target package name case-insensitively
    # with normalization.
    target_norm = name.lower().replace('_', '-')
    dists = [
        d for d in dists
        if d.name.lower().replace('_', '-') == target_norm
    ]

    deleted_files = []
    for dist in dists:
        libdir = dist.path.parent
        files = dist.get_installed_files()
        for file in files:
            path = libdir / file
            if path.is_file():
                logger.debug(f'Removing {path}')
                try:
                    path.unlink()
                    deleted_files.append(path)
                except OSError as e:
                    logger.warning(f"Could not remove file '{path}': {e}")

    # Explicitly track and clean up residual egg-links in case the
    # distribution files list did not fully cover them.
    for libdir in libdirs:
        for n in (name, name.replace('_', '-')):
            egg_link = libdir / f'{n}.egg-link'
            if egg_link.is_file():
                logger.debug(f'Removing egg-link {egg_link}')
                try:
                    egg_link.unlink()
                    deleted_files.append(egg_link)
                except OSError as e:
                    logger.warning(
                        f"Could not remove egg-link '{egg_link}': {e}"
                    )

    # Clean up empty parent directories recursively
    parent_dirs = set()
    for file in deleted_files:
        for parent in enumerate_parent_dirs(file, install_base):
            parent_dirs.add(parent)

    for parent in sorted(parent_dirs, reverse=True):
        try:
            parent.rmdir()
            logger.debug(f'Removing empty directory {parent}' + os.path.sep)
        except OSError:
            # Directory is not empty or cannot be removed
            pass


def enumerate_parent_dirs(file, base):
    """
    Enumerate all recursive directories under a base directory to a file.

    The base directory itself is not enumerated.

    :param Path file: The file under the base directory
    :param Path base: The base directory
    :returns: Generator of parent directories
    :rtype: Generator[Path, None, None]
    """
    try:
        rel = file.parent.relative_to(base)
    except ValueError:
        return
    for i in range(1, len(rel.parts) + 1):
        yield base.joinpath(*rel.parts[:i])
