# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import sleep

from colcon_core import location
from colcon_core.location import create_log_path
from colcon_core.location import get_config_path
from colcon_core.location import get_log_path
from colcon_core.location import set_default_config_path
from colcon_core.location import set_default_log_path
from mock import patch
import pytest

from .environment_context import EnvironmentContext


@pytest.fixture(scope='module', autouse=True)
def reset_global_variables():
    yield
    from colcon_core import location
    assert location._log_base_path is not None
    location._config_path = None
    location._config_path_env_var = None
    location._log_base_path = None
    location._log_base_path_env_var = None
    location._log_subdirectory = None


def test_config_path():
    # use config path
    config_path = '/some/path'.replace('/', os.sep)
    with patch('colcon_core.location.logger.info') as info:
        set_default_config_path(path=config_path)
        info.assert_called_once_with(
            "Using config path '{config_path}'".format_map(locals()))

    # use config path if environment variable is not set
    config_path_env_var = 'TEST_COLCON_CONFIG_PATH'
    with patch('colcon_core.location.logger.info') as info:
        set_default_config_path(
            path=config_path, env_var=config_path_env_var)
        info.assert_called_once_with(
            "Using config path '{config_path}'".format_map(locals()))

    # use environment variable when set
    config_path = '/other/path'.replace('/', os.sep)
    with EnvironmentContext(**{config_path_env_var: config_path}):
        assert isinstance(get_config_path(), Path)
        assert str(get_config_path()) == config_path


def test_log_path():
    # use log base path
    log_base_path = '/some/path'.replace('/', os.sep)
    set_default_log_path(base_path=log_base_path)
    assert isinstance(get_log_path(), Path)
    assert str(get_log_path().parent) == log_base_path

    # use log base path if environment variable is not set
    log_base_path_env_var = 'TEST_COLCON_LOG_BASE_PATH'
    set_default_log_path(
        base_path=log_base_path, env_var=log_base_path_env_var)
    assert isinstance(get_log_path(), Path)
    assert str(get_log_path().parent) == log_base_path

    # use environment variable when set
    log_base_path = '/other/path'.replace('/', os.sep)
    with EnvironmentContext(**{log_base_path_env_var: log_base_path}):
        assert isinstance(get_log_path(), Path)
        assert str(get_log_path().parent) == log_base_path

    # use specific subdirectory
    subdirectory = 'sub'
    with patch('colcon_core.location.logger.info') as info:
        set_default_log_path(
            base_path=log_base_path, env_var=log_base_path_env_var,
            subdirectory=subdirectory)
        assert isinstance(get_log_path(), Path)
        assert get_log_path() == Path(log_base_path) / subdirectory
        info.assert_called_once_with(
            "Using log path '{log_base_path}/{subdirectory}'"
            .format_map(locals()).replace('/', os.sep))


def test_create_log_path():
    # no need to create a directory if the path already exists
    log_path = Path(os.getcwd())
    set_default_log_path(
        base_path=log_path.parent, subdirectory=log_path.name)
    with patch('os.makedirs') as makedirs:
        makedirs.side_effect = AssertionError('should not be called')
        create_log_path('verb')
    # no latest symlink is being created either
    assert not (log_path.parent / 'latest').exists()

    subdirectory = 'sub'
    with TemporaryDirectory(prefix='test_colcon_') as log_path:
        log_path = Path(log_path)

        # create a directory and symlink when the path doesn't exist
        set_default_log_path(base_path=log_path, subdirectory=subdirectory)
        with patch('os.makedirs', wraps=os.makedirs) as makedirs:
            create_log_path('verb')
            makedirs.assert_called_once_with(
                str(log_path / subdirectory), exist_ok=True)
        assert (log_path / subdirectory).exists()

        # skip all symlink tests on Windows for now
        if sys.platform == 'win32':
            return

        # check that `latest_verb` was created and points to the subdirectory
        assert (log_path / 'latest_verb').is_symlink()
        assert (log_path / 'latest_verb').resolve() == \
            (log_path / subdirectory).resolve()

        # check that `latest` was created and points to the subdirectory
        assert (log_path / 'latest').is_symlink()
        assert (log_path / 'latest').resolve() == \
            (log_path / subdirectory).resolve()

        # create directory but correct latest symlink already exists
        (log_path / subdirectory).rmdir()
        create_log_path('verb')
        assert (log_path / subdirectory).exists()
        assert (log_path / 'latest').is_symlink()
        assert (log_path / 'latest').resolve() == \
            (log_path / subdirectory).resolve()

        # create directory and update latest symlink
        subdirectory = 'other_sub'
        set_default_log_path(base_path=log_path, subdirectory=subdirectory)
        create_log_path('verb')
        assert (log_path / subdirectory).exists()
        assert (log_path / 'latest').is_symlink()
        assert (log_path / 'latest').resolve() == \
            (log_path / subdirectory).resolve()

        # create directory but latest is not a symlink
        (log_path / subdirectory).rmdir()
        (log_path / 'latest').unlink()
        (log_path / 'latest').mkdir()
        create_log_path('verb')
        assert (log_path / subdirectory).exists()
        assert not (log_path / 'latest').is_symlink()


def test_create_log_path_race():
    # check race if log path is created at the same time
    subdirectory = 'sub'
    with TemporaryDirectory(prefix='test_colcon_') as log_path:
        log_path = Path(log_path)

        set_default_log_path(base_path=log_path, subdirectory=subdirectory)

        # spawn thread which hold the lock for some time
        def hold_lock_for_some_time():
            with location._create_log_path_lock:
                sleep(1)
                (log_path / subdirectory).mkdir()
        Thread(target=hold_lock_for_some_time).start()

        with patch('os.makedirs') as makedirs:
            makedirs.side_effect = AssertionError('should not be called')
            create_log_path('verb')
        # no latest symlink is being created either
        assert not (log_path / 'latest').exists()
