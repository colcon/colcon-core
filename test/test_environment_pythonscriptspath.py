# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from unittest.mock import patch

from colcon_core.environment.path import PythonScriptsPathEnvironment
from colcon_core.python_install_path import get_python_install_path


def test_path(tmp_path):
    extension = PythonScriptsPathEnvironment()

    scripts_path = get_python_install_path('scripts', {'base': tmp_path})
    with patch(
        'colcon_core.shell.create_environment_hook',
        return_value=['/some/hook', '/other/hook'],
    ):
        # bin directory does not exist
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 0

        # bin directory exists, but empty
        scripts_path.mkdir()
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 0

        # bin directory exists, but only subdirectories
        (scripts_path / 'subdir').mkdir()
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 0

        # bin directory exists, with file
        (scripts_path / 'hook').write_text('')
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 2

        # bin directory exists, with files
        (scripts_path / 'hook2').write_text('')
        hooks = extension.create_environment_hooks(tmp_path, 'pkg_name')
        assert len(hooks) == 2
