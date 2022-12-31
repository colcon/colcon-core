# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from colcon_core.environment.pythonpath import PythonPathEnvironment
from colcon_core.python_install_path import get_python_install_path


def test_pythonpath():
    extension = PythonPathEnvironment()

    with TemporaryDirectory(prefix='test_colcon_') as prefix_path:
        prefix_path = Path(prefix_path)
        with patch(
            'colcon_core.shell.create_environment_hook',
            return_value=['/some/hook', '/other/hook']
        ):
            # Python path does not exist
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 0

            # Python path exists
            python_path = get_python_install_path(
                'purelib', {'base': prefix_path})
            python_path.mkdir(parents=True)
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 2
