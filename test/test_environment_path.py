# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.environment.path import PathEnvironment
from mock import patch


def test_path():
    extension = PathEnvironment()

    with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
        prefix_path = Path(prefix_path)
        with patch(
            'colcon_core.shell.create_environment_hook',
            return_value=['/some/hook', '/other/hook']
        ):
            # bin directory does not exist
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 0

            # bin directory exists, but empty
            (prefix_path / 'bin').mkdir()
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 0

            # bin directory exists, but only subdirectories
            (prefix_path / 'bin' / 'subdir').mkdir()
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 0

            # bin directory exists, with file
            (prefix_path / 'bin' / 'hook').write_text('')
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 2

            # bin directory exists, with files
            (prefix_path / 'bin' / 'hook2').write_text('')
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 2
