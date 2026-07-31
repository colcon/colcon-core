# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Uninstallation and cleanup utilities for Python packages."""

from base64 import urlsafe_b64encode
from configparser import ConfigParser
from functools import lru_cache
from email import message_from_binary_file
from hashlib import sha256
from io import TextIOWrapper
import os
from pathlib import Path
import shutil
import warnings
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from colcon_core.logging import colcon_logger
from colcon_core.python_project.distribution import _get_install_path
from colcon_core.python_project.distribution import InstalledDistribution
from distlib.scripts import ScriptMaker

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


@lru_cache(maxsize=32)
def _get_script_maker(script_dir, dry_run=False):
    """
    Get a ScriptMaker instance.

    :param Path script_dir: Directory where scripts will be created
    :param bool dry_run: If True, do not write scripts to disk
    :returns: ScriptMaker instance
    :rtype: ScriptMaker
    """
    sm = ScriptMaker(None, str(script_dir), dry_run=dry_run)
    sm.clobber = True
    sm.variants = {''}
    return sm


def write_and_record(libdir, path, lines):
    """
    Write file content to disk and compute a fully-qualified RECORD entry.

    :param Path libdir: Library directory where package is installed
    :param str/Path path: Path to file to write relative to libdir
    :param list[str] lines: Lines of text to write
    :returns: Three-element tuple constituting the file's RECORD entry
    :rtype: tuple[str, str, str]
    """
    path = libdir / path
    raw = (os.linesep.join(lines) + os.linesep).encode()
    digest = urlsafe_b64encode(sha256(raw).digest()).rstrip(b'=').decode()
    path.write_bytes(raw)
    return (
        Path(os.path.relpath(path, libdir)).as_posix(),
        f'sha256={digest}',
        f'{len(raw)}')


def install_wheel(wheel_path, install_base, script_dir_override=None):
    """
    Install a wheel file under the given installation base directory.

    :param Path wheel_path: Path to the wheel file to be installed
    :param Path install_base: Path to the base directory to install under
    :param str script_dir_override: Optional path override for scripts
    :returns: Path to the installed distribution info directory
    :rtype: Path
    :raises RuntimeError: If the wheel format is invalid or unsupported
    """
    wheel_name = wheel_path.name.split('-')
    if len(wheel_name) not in (5, 6):
        raise RuntimeError('Invalid wheel file name')
    distribution, version = wheel_name[:2]
    dist_info_dir = f'{distribution}-{version}.dist-info/'
    data_dir = f'{distribution}-{version}.data/'
    wheel_file = dist_info_dir + 'WHEEL'
    record_file = dist_info_dir + 'RECORD'
    entry_points_file = dist_info_dir + 'entry_points.txt'

    install_base = Path(install_base)

    remove_distributions(distribution, install_base)

    with ZipFile(
        wheel_path, mode='r', compression=ZIP_DEFLATED, allowZip64=True
    ) as wf:
        with wf.open(wheel_file) as wf_mf:
            wheel_metadata = message_from_binary_file(wf_mf)

        wheel_version = wheel_metadata.get('Wheel-Version', '').split('.')
        if len(wheel_version) < 2 or wheel_version[0] != '1':
            raise RuntimeError('Wheel file is not supported')
        elif wheel_version[1] != '0':
            warnings.warn('Wheel format is newer than supported version')

        if wheel_metadata.get('Root-Is-Purelib') in ('true',):
            libdir = Path(_get_install_path('purelib', install_base))
        else:
            libdir = Path(_get_install_path('platlib', install_base))

        records = []
        with wf.open(record_file) as wf_rec_bin:
            with TextIOWrapper(wf_rec_bin) as wf_rec:
                for line in wf_rec:
                    if ',' in line:
                        records.append(line.strip().split(','))

        for record in records:
            if record[0] == record_file:
                continue
            elif not record[0].startswith(data_dir):
                wf.extract(record[0], libdir)
                continue

            _, key, subpath = record[0].split('/', 2)
            target = Path(_get_install_path(key, install_base))
            target /= subpath
            target.parent.mkdir(parents=True, exist_ok=True)
            with wf.open(record[0]) as fsrc:
                with target.open('wb') as fdst:
                    shutil.copyfileobj(fsrc, fdst)
            record[0] = os.path.relpath(target, start=libdir)

        records.append(write_and_record(
            libdir,
            dist_info_dir + 'INSTALLER',
            ('colcon-core',)))

        if entry_points_file in wf.namelist():
            ep = ConfigParser()
            with wf.open(entry_points_file) as wf_ep_bin:
                with TextIOWrapper(wf_ep_bin) as wf_ep:
                    ep.read_file(wf_ep)
            if ep.has_section('console_scripts'):
                if script_dir_override:
                    script_dir = install_base / script_dir_override
                else:
                    script_dir = Path(
                        _get_install_path('scripts', install_base))
                sm = _get_script_maker(script_dir)
                specs = [
                    '%s = %s' % pair
                    for pair in ep.items('console_scripts')
                ]
                scripts_made = sm.make_multiple(specs)

                records += [
                    (Path(os.path.relpath(s, libdir)).as_posix(), '', '')
                    for s in scripts_made
                ]

        with (libdir / record_file).open('w') as f:
            f.writelines(','.join(rec) + '\n' for rec in records)

        return libdir / dist_info_dir
