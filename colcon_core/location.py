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


def create_log_path():
    """
    Create the logging directory if it doesn't exist yet.

    On non-Windows platforms a symlink named `latest` is created in the base
    path which links to the subdirectory.
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

        # create latest symlink
        if sys.platform == 'win32':
            return
        latest = path.parent / 'latest'
        if latest.exists():
            # directory exists or valid symlink
            if not latest.is_symlink():
                # do not change non symlink paths
                return
            if latest.resolve() == path.resolve():
                # desired symlink already exists
                return
        # remove valid symlink to wrong destination (if)
        # or invalid symlink (else)
        if latest.is_symlink():
            os.remove(str(latest))

        os.symlink(str(path), str(latest))
