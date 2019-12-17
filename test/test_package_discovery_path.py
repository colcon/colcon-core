# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_discovery.path import _expand_wildcards
from colcon_core.package_discovery.path import PathPackageDiscovery
from colcon_core.package_identification import IgnoreLocationException
from mock import Mock
from mock import patch


def test_path_package_discovery():
    extension = PathPackageDiscovery()
    assert extension.has_default() is True


def test_add_arguments():
    extension = PathPackageDiscovery()
    parser = Mock()
    parser.add_argument = Mock()
    extension.add_arguments(parser=parser, with_default=True)
    assert parser.add_argument.call_count == 1


def test_has_parameters():
    extension = PathPackageDiscovery()
    args = Mock()
    args.paths = []
    assert extension.has_parameters(args=args) is False
    args.paths = ['/some/path']
    assert extension.has_parameters(args=args) is True


def identify(_, path):
    if path == '/empty/path':
        return None
    if path == '/skip/path':
        raise IgnoreLocationException()
    return PackageDescriptor(path)


def test_discover():
    extension = PathPackageDiscovery()
    args = Mock()
    args.paths = None
    assert extension.discover(args=args, identification_extensions={}) == set()

    args.paths = [
        '/empty/path',
        '/skip/path',
        '/same/path', '/same/path/../path',
        '/other/path']
    with patch(
        'colcon_core.package_discovery.path.identify', side_effect=identify
    ):
        descs = extension.discover(args=args, identification_extensions={})
        assert descs == {
            PackageDescriptor(os.path.realpath('/same/path')),
            PackageDescriptor(os.path.realpath('/other/path'))}


def test__expand_wildcards():
    with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
        prefix_path = Path(prefix_path)
        (prefix_path / 'one').mkdir()
        (prefix_path / 'two').mkdir()
        (prefix_path / 'three').touch()

        paths = [
            '/some/path',
            str(prefix_path / '*')
        ]
        _expand_wildcards(paths)
        assert len(paths) == 3
        assert paths[0] == '/some/path'
        assert paths[1] == str((prefix_path / 'one'))
        assert paths[2] == str((prefix_path / 'two'))
