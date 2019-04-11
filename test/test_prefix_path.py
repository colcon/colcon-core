# Copyright 2019 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.prefix_path import get_chained_prefix_path
from colcon_core.prefix_path import get_prefix_path_extensions
from colcon_core.prefix_path import PrefixPathExtensionPoint
from colcon_core.prefix_path.colcon import ColconPrefixPath
from mock import Mock
from mock import patch
import pytest

from .entry_point_context import EntryPointContext
from .environment_context import EnvironmentContext


class Extension1(PrefixPathExtensionPoint):
    PRIORITY = 90


class Extension2(PrefixPathExtensionPoint):
    pass


def test_extension_interface():
    extension = Extension1()
    with pytest.raises(NotImplementedError):
        extension.extend_prefix_path(None)


def test_get_prefix_path_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_prefix_path_extensions()
    assert list(extensions.keys()) == [100, 90]
    assert list(extensions[100].keys()) == ['extension2']
    assert list(extensions[90].keys()) == ['extension1']


def test_get_chained_prefix_path():
    # empty environment variable
    with EnvironmentContext(COLCON_PREFIX_PATH=''):
        prefix_path = get_chained_prefix_path()
        assert prefix_path == []

    # extra path separator
    with EnvironmentContext(COLCON_PREFIX_PATH=os.pathsep):
        prefix_path = get_chained_prefix_path(skip='/path/to/skip')
        assert prefix_path == []

    ColconPrefixPath.PREFIX_PATH_NAME = 'colcon'
    with patch(
        'colcon_core.prefix_path.get_prefix_path_extensions',
        return_value={
            100: {'colcon': ColconPrefixPath()},
        }
    ):
        with TemporaryDirectory(prefix='test_colcon_') as basepath:
            basepath = Path(basepath)
            with EnvironmentContext(COLCON_PREFIX_PATH=os.pathsep.join(
                [str(basepath), str(basepath)]
            )):
                # multiple results, duplicates being skipped
                prefix_path = get_chained_prefix_path(skip='/path/to/skip')
                assert prefix_path == [str(basepath)]

                # skipping results
                prefix_path = get_chained_prefix_path(skip=str(basepath))
                assert prefix_path == []

            # skipping non-existing results
            with EnvironmentContext(COLCON_PREFIX_PATH=os.pathsep.join(
                [str(basepath), str(basepath / 'non-existing-sub')]
            )):
                with patch(
                    'colcon_core.prefix_path.colcon.logger.warning'
                ) as warn:
                    prefix_path = get_chained_prefix_path()
                assert prefix_path == [str(basepath)]
                assert warn.call_count == 1
                assert len(warn.call_args[0]) == 1
                assert warn.call_args[0][0].endswith(
                    "non-existing-sub' in the environment variable "
                    "COLCON_PREFIX_PATH doesn't exist")
                # suppress duplicate warning
                with patch(
                    'colcon_core.prefix_path.colcon.logger.warning'
                ) as warn:
                    prefix_path = get_chained_prefix_path()
                assert prefix_path == [str(basepath)]
                assert warn.call_count == 0

    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_prefix_path_extensions()

        # one invalid return value, one not implemented
        extensions[100]['extension2'].extend_prefix_path = Mock(
            return_value=False)
        extensions[90]['extension1'].extend_prefix_path = Mock(
            return_value=None)
        with patch('colcon_core.prefix_path.logger.error') as error:
            get_chained_prefix_path()
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args_list[0][0]) == 1
        assert error.call_args_list[0][0][0].startswith(
            "Exception in prefix path extension 'extension2': "
            'extend_prefix_path() should return None\n')
