# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core import location
from colcon_core.location import _create_symlink
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
    location._create_log_path_called = False
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
    # use explicitly passed log base path even if environment variable is set
    with EnvironmentContext(**{log_base_path_env_var: '/not/used'}):
        assert isinstance(get_log_path(), Path)
        assert str(get_log_path().parent) == log_base_path

    # suppress logging when environment variable is set to devnull
    set_default_log_path(base_path=os.devnull)
    assert get_log_path() is None

    # use environment variable when set and no base path passed
    log_base_path = '/other/path'.replace('/', os.sep)
    set_default_log_path(
        base_path=None, env_var=log_base_path_env_var)
    with EnvironmentContext(**{log_base_path_env_var: log_base_path}):
        assert isinstance(get_log_path(), Path)
        assert str(get_log_path().parent) == log_base_path

    # use default if not environment variable is set and no base path passed
    set_default_log_path(
        base_path=None, env_var=log_base_path_env_var, default='some_default')
    assert isinstance(get_log_path(), Path)
    assert str(get_log_path().parent) == 'some_default'

    # use specific subdirectory
    subdirectory = 'sub'
    set_default_log_path(
        base_path=log_base_path, env_var=log_base_path_env_var,
        subdirectory=subdirectory)
    assert isinstance(get_log_path(), Path)
    assert get_log_path() == Path(log_base_path) / subdirectory


def test_create_log_path():
    subdirectory = 'sub'
    with TemporaryDirectory(prefix='test_colcon_') as log_path:
        log_path = Path(log_path)
        set_default_log_path(base_path=log_path, subdirectory=subdirectory)

        # create a directory and symlink when the path doesn't exist
        with patch('os.makedirs', wraps=os.makedirs) as makedirs:
            create_log_path('verb')
            makedirs.assert_called_once_with(str(log_path / subdirectory))
        assert (log_path / subdirectory).exists()

        # repeated call is a noop
        with patch('os.makedirs') as makedirs:
            makedirs.side_effect = AssertionError('should not be called')
            create_log_path('verb')

        # since the directory already exists create one with a suffix
        location._create_log_path_called = False
        with patch('os.makedirs', wraps=os.makedirs) as makedirs:
            create_log_path('verb')
            assert makedirs.call_count == 2
            assert len(makedirs.call_args_list[0][0]) == 1
            assert makedirs.call_args_list[0][0][0] == str(
                log_path / subdirectory)
            assert len(makedirs.call_args_list[1][0]) == 1
            assert makedirs.call_args_list[1][0][0] == str(
                log_path / subdirectory) + '_2'
        assert (log_path / (str(subdirectory) + '_2')).exists()

        # and another increment of the suffix
        location._create_log_path_called = False
        location._log_subdirectory = subdirectory
        with patch('os.makedirs', wraps=os.makedirs) as makedirs:
            create_log_path('verb')
            assert makedirs.call_count == 3
            assert len(makedirs.call_args_list[0][0]) == 1
            assert makedirs.call_args_list[0][0][0] == str(
                log_path / subdirectory)
            assert len(makedirs.call_args_list[1][0]) == 1
            assert makedirs.call_args_list[1][0][0] == str(
                log_path / subdirectory) + '_2'
            assert len(makedirs.call_args_list[2][0]) == 1
            assert makedirs.call_args_list[2][0][0] == str(
                log_path / subdirectory) + '_3'
        assert (log_path / (str(subdirectory) + '_3')).exists()
        subdirectory += '_3'

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
        location._create_log_path_called = False
        create_log_path('verb')
        assert (log_path / subdirectory).exists()
        assert (log_path / 'latest').is_symlink()
        assert (log_path / 'latest').resolve() == \
            (log_path / subdirectory).resolve()

        # create directory and update latest symlink
        subdirectory = 'other_sub'
        set_default_log_path(base_path=log_path, subdirectory=subdirectory)
        location._create_log_path_called = False
        create_log_path('verb')
        assert (log_path / subdirectory).exists()
        assert (log_path / 'latest').is_symlink()
        assert (log_path / 'latest').resolve() == \
            (log_path / subdirectory).resolve()

        # create directory but latest is not a symlink
        (log_path / subdirectory).rmdir()
        (log_path / 'latest').unlink()
        (log_path / 'latest').mkdir()
        location._create_log_path_called = False
        create_log_path('verb')
        assert (log_path / subdirectory).exists()
        assert not (log_path / 'latest').is_symlink()


def test__create_symlink():
    # check cases where functions raise exceptions and ensure it is being
    # handled gracefully
    with TemporaryDirectory(prefix='test_colcon_') as path:
        path = Path(path)

        # relative path couldn't be computed, symlink couldn't be created
        _create_symlink(path / 'nowhere', Path('/foo/bar'))

        # unlinking symlink failed
        class DummyPath:

            def __init__(self):
                self.parent = 'parent'

            def exists(self):
                return False

            def is_symlink(self):
                return True

            def unlink(self):
                raise FileNotFoundError()

        with patch('os.symlink') as symlink:
            _create_symlink(path / 'src', DummyPath())
            assert symlink.call_count == 1

        # (Windows) OSError: symbolic link privilege not held
        class ValidPath(DummyPath):

            def is_symlink(self):
                return False

        with patch('os.symlink') as symlink:
            symlink.side_effect = OSError()
            _create_symlink(path / 'src', ValidPath())
            assert symlink.call_count == 1
