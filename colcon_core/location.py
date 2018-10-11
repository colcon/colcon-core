# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
import sys
from threading import Lock
import uuid

from colcon_core.logging import colcon_logger

logger = colcon_logger.getChild(__name__)

_config_path = None
_config_path_env_var = None
_log_base_path = None
_log_base_path_env_var = None
_log_subdirectory = None


def get_config_path():
    """
    Get the base path for configuration files.

    :function:`set_default_config_path` must have been called before.

    :returns: The base path for configuration files
    :rtype: Path
    """
    global _config_path_env_var
    if _config_path_env_var is not None:
        path = os.environ.get(_config_path_env_var)
        if path:
            return Path(str(path))
    global _config_path
    assert _config_path is not None
    return _config_path


def set_default_config_path(*, path, env_var=None):
    """
    Set the base path for configuration files.

    Optionally an environment variable name can be provided which if set will
    override the configured base path.

    An info message is logged which states the used path.

    :param path: The base path
    :param str env_var: The name of the environment variable
    """
    global _config_path
    global _config_path_env_var
    _config_path = Path(str(path))
    _config_path_env_var = env_var
    config_path = get_config_path()
    logger.info("Using config path '{config_path}'".format_map(locals()))


def get_log_path():
    """
    Get the base path for logging.

    :function:`set_default_log_path` must have been called before.

    :returns: The base path for logging
    :rtype: Path
    """
    global _log_base_path_env_var
    path = None
    if _log_base_path_env_var is not None:
        path = os.environ.get(_log_base_path_env_var)
        if path:
            path = Path(str(path))
    global _log_base_path
    if not path:
        assert _log_base_path is not None
        path = _log_base_path
    path /= _log_subdirectory
    return path


def set_default_log_path(*, base_path, env_var=None, subdirectory=None):
    """
    Set the base path for logging.

    Optionally an environment variable name can be provided which if set will
    override the configured base path.

    An info message is logged which states the used path.

    :param base_path: The base path
    :param str env_var: The name of the environment variable
    :param str subdirectory: The name of the subdirectory, if not provided a
      random uuid will be used instead
    """
    global _log_base_path
    global _log_base_path_env_var
    global _log_subdirectory
    _log_base_path = Path(str(base_path))
    _log_base_path_env_var = env_var
    assert subdirectory is None or subdirectory
    _log_subdirectory = subdirectory \
        if subdirectory is not None \
        else str(uuid.uuid4())
    logger.info("Using log path '%s'" % get_log_path())


_create_log_path_lock = Lock()


def create_log_path(verb_name):
    """
    Create the logging directory if it doesn't exist yet.

    On non-Windows platforms two symlinks are created as siblings of the log
    path:
    * `latest_<verb_name>` linking to the log path
    * `latest` linking to `latest_<verb_name>`

    :param str verb_name: The verb name
    """
    path = get_log_path()
    if path.exists():
        return

    global _create_log_path_lock
    with _create_log_path_lock:
        # check again with lock
        if path.exists():
            return
        os.makedirs(str(path), exist_ok=True)

        # ensure the base log path has an ignore marker file
        # to avoid recursively crawling through log directories
        from colcon_core.package_identification.ignore import IGNORE_MARKER
        ignore_marker = path.parent / IGNORE_MARKER
        if not ignore_marker.exists():
            with ignore_marker.open('w'):
                pass

        # create latest symlinks
        if sys.platform == 'win32':
            return
        _create_symlink(
            path, path.parent / 'latest_{verb_name}'.format_map(locals()))
        _create_symlink(
            path.parent / 'latest_{verb_name}'.format_map(locals()),
            path.parent / 'latest')


def _create_symlink(src, dst):
    if dst.exists():
        # directory exists or valid symlink
        if not dst.is_symlink():
            # do not change non symlink paths
            return
        if dst.resolve() == src.resolve():
            # desired symlink already exists
            return
    # remove valid symlink to wrong destination (if)
    # or invalid symlink (else)
    if dst.is_symlink():
        os.remove(str(dst))

    # use relative path when possible
    try:
        src = src.relative_to(dst.parent)
    except ValueError:
        pass
    os.symlink(str(src), str(dst))


def get_relative_package_index_path():
    """
    Get the prefix-relative path to the package index.

    :returns: The relative path to the package index
    :rtype: Path
    """
    # the value is also being hard coded in shell/template/prefix_util.py
    return Path('share', 'colcon-core', 'packages')
