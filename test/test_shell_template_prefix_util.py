# Copyright 2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.location import get_relative_package_index_path
from colcon_core.shell.template.prefix_util import get_packages
from colcon_core.shell.template.prefix_util import main
from colcon_core.shell.template.prefix_util import order_packages
from colcon_core.shell.template.prefix_util import reduce_cycle_set
from mock import patch
import pytest


def test_main(capsys):
    with patch(
        'colcon_core.shell.template.prefix_util.get_packages',
        return_value={'pkgA': set()}
    ):
        main([])
    out, err = capsys.readouterr()
    assert out == 'pkgA\n'
    assert not err


def test_get_packages():
    with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
        prefix_path = Path(prefix_path)

        # check no packages in not merged install layout
        packages = get_packages(prefix_path, False)
        assert packages == {}

        # mock packages in not merged install layout
        subdirectory = get_relative_package_index_path()
        for pkg_name in ('pkgA', 'pkgB'):
            (prefix_path / pkg_name / subdirectory).mkdir(parents=True)
            (prefix_path / pkg_name / subdirectory / pkg_name).write_text(
                'depX')
        (prefix_path / 'dummy_dir').mkdir()
        (prefix_path / '.hidden_dir').mkdir()
        (prefix_path / 'dummy_file').write_text('')

        # check no packages in merged install layout
        packages = get_packages(prefix_path, True)
        assert packages == {}

        # mock packages in merged install layout
        (prefix_path / subdirectory).mkdir(parents=True)
        (prefix_path / subdirectory / 'pkgB').write_text('')
        (prefix_path / subdirectory / 'pkgC').write_text(
            os.pathsep.join(('pkgB', 'depC')))
        (prefix_path / subdirectory / 'dummy_dir').mkdir()
        (prefix_path / subdirectory / '.hidden_file').write_text('')

        # check packages and dependencies in not merged install layout
        packages = get_packages(prefix_path, False)
        assert len(packages) == 2
        assert 'pkgA' in packages
        assert packages['pkgA'] == set()
        assert 'pkgB' in packages
        assert packages['pkgB'] == set()

        # check packages and dependencies in not merged install layout
        packages = get_packages(prefix_path, True)
        assert len(packages) == 2
        assert 'pkgB' in packages
        assert packages['pkgB'] == set()
        assert 'pkgC' in packages
        assert packages['pkgC'] == {'pkgB'}


def test_order_packages():
    packages = {
        'pkgA': {'pkgC'},
        'pkgB': {},
        'pkgC': {},
    }
    ordered = order_packages(packages)
    assert ordered == ['pkgB', 'pkgC', 'pkgA']

    packages = {
        'pkgA': {'pkgB'},
        'pkgB': {'pkgA'},
        'pkgC': set(),
    }
    with pytest.raises(RuntimeError) as e:
        ordered = order_packages(packages)
    assert 'Circular dependency between:' in str(e.value)
    assert 'pkgA' in str(e.value)
    assert 'pkgB' in str(e.value)
    assert 'pkgC' not in str(e.value)


def test_reduce_cycle_set():
    packages = {
        'pkgA': {'pkgB'},
        'pkgB': set(),
    }
    reduce_cycle_set(packages)
    assert len(packages) == 0
