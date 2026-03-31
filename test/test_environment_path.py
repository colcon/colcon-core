# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from unittest.mock import patch

from colcon_core.environment.path import PathEnvironment


def test_path(tmp_path):
    extension = PathEnvironment()

    with patch(
        'colcon_core.shell.create_environment_hook',
        return_value=['/some/hook', '/other/hook']
    ):
        # bin directory does not exist
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 0

        # bin directory exists, but empty
        (tmp_path / 'bin').mkdir()
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 0

        # bin directory exists, but only subdirectories
        (tmp_path / 'bin' / 'subdir').mkdir()
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 0

        # bin directory exists, with file
        (tmp_path / 'bin' / 'hook').write_text('')
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 2

        # bin directory exists, with files
        (tmp_path / 'bin' / 'hook2').write_text('')
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 2
