# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import argparse
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.verb import check_and_mark_build_tool
from colcon_core.verb import check_and_mark_install_layout
from colcon_core.verb import get_verb_extensions
from colcon_core.verb import update_object
from colcon_core.verb import VerbExtensionPoint
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


def test_verb_interface():
    assert hasattr(VerbExtensionPoint, 'EXTENSION_POINT_VERSION')
    interface = VerbExtensionPoint()
    interface.add_arguments(parser=None)
    with pytest.raises(NotImplementedError):
        interface.main(context=None)


class Extension1(VerbExtensionPoint):
    pass


class Extension2(VerbExtensionPoint):
    pass


def test_get_verb_extensions():
    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        extensions = get_verb_extensions()
    assert list(extensions.keys()) == ['extension1', 'extension2']


def test_check_and_mark_build_tool():
    with TemporaryDirectory(prefix='test_colcon_') as base_path:
        base_path = Path(base_path)

        # create marker if it doesn't exist
        check_and_mark_build_tool(str(base_path))
        marker_path = base_path / '.built_by'
        assert marker_path.exists()
        assert marker_path.read_text().rstrip() == 'colcon'

        # create path and marker if it doesn't exist
        path = base_path / 'no_base'
        check_and_mark_build_tool(str(path))
        assert path.exists()
        marker_path = path / '.built_by'
        assert marker_path.exists()
        assert marker_path.read_text().rstrip() == 'colcon'

        # existing marker with same content
        path = base_path / 'existing_marker'
        path.mkdir()
        marker_path = path / '.built_by'
        marker_path.write_text('colcon')
        check_and_mark_build_tool(str(path))
        assert marker_path.exists()
        assert marker_path.read_text().rstrip() == 'colcon'

        # existing marker with different content
        marker_path.write_text('other')
        with pytest.raises(RuntimeError):
            check_and_mark_build_tool(str(path))


def test_check_and_mark_install_layout():
    with TemporaryDirectory(prefix='test_colcon_') as base_path:
        base_path = Path(base_path)

        # create marker if it doesn't exist
        check_and_mark_install_layout(str(base_path), merge_install=False)
        marker_path = base_path / '.colcon_install_layout'
        assert marker_path.exists()
        assert marker_path.read_text().rstrip() == 'isolated'

        # create path and marker if it doesn't exist
        path = base_path / 'no_base'
        check_and_mark_install_layout(str(path), merge_install=True)
        assert path.exists()
        marker_path = path / '.colcon_install_layout'
        assert marker_path.exists()
        assert marker_path.read_text().rstrip() == 'merged'

        # existing marker with same content
        check_and_mark_install_layout(str(path), merge_install=True)
        assert marker_path.exists()
        assert marker_path.read_text().rstrip() == 'merged'

        # existing marker with different content
        with pytest.raises(RuntimeError):
            check_and_mark_install_layout(str(path), merge_install=False)

        # install base which is a file
        with pytest.raises(RuntimeError):
            check_and_mark_install_layout(str(marker_path), merge_install=True)


def test_update_object():
    obj = argparse.Namespace()
    key = 'key'
    msg_args = ['package_name', 'argument_type', 'value_source']
    update_object(obj, key, 'foo', *msg_args)
    assert hasattr(obj, key)
    assert getattr(obj, key) == 'foo'

    # debug message when overwriting a value with the same type
    with patch('colcon_core.verb.logger.log') as log:
        update_object(obj, key, 'bar', *msg_args)
    assert getattr(obj, key) == 'bar'
    assert log.call_count == 1
    assert len(log.call_args[0]) == 2
    assert log.call_args[0][0] == 5
    assert 'overwrite' in log.call_args[0][1]

    # warning message when overwriting a value with a different type
    with patch('colcon_core.verb.logger.log') as log:
        update_object(obj, key, 42, *msg_args)
    assert getattr(obj, key) == 42
    assert log.call_count == 1
    assert len(log.call_args[0]) == 2
    assert log.call_args[0][0] == logging.WARNING
    assert 'overwrite' in log.call_args[0][1]

    # an existing dictionary value is updated with the passed dictionary
    obj = argparse.Namespace()
    update_object(obj, key, {'foo': 'foo', 'bar': 'bar'}, *msg_args)
    with patch('colcon_core.verb.logger.log') as log:
        update_object(obj, key, {'bar': 'BAR', 'baz': 'BAZ'}, *msg_args)
    assert getattr(obj, key) == {'foo': 'foo', 'bar': 'BAR', 'baz': 'BAZ'}
    assert log.call_count == 1
    assert len(log.call_args[0]) == 2
    assert log.call_args[0][0] == 5
    assert 'update' in log.call_args[0][1]

    # an existing list value is extended with the passed list
    obj = argparse.Namespace()
    update_object(obj, key, ['foo', 'bar'], *msg_args)
    with patch('colcon_core.verb.logger.log') as log:
        update_object(obj, key, ['bar', 'baz'], *msg_args)
    assert getattr(obj, key) == ['foo', 'bar', 'bar', 'baz']
    assert log.call_count == 1
    assert len(log.call_args[0]) == 2
    assert log.call_args[0][0] == 5
    assert 'extend' in log.call_args[0][1]
