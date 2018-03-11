# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from distutils.sysconfig import get_python_lib
from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.environment.pythonpath import PythonPathEnvironment
from mock import patch


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
            python_path = Path(get_python_lib(prefix=str(prefix_path)))
            python_path.mkdir(parents=True)
            hooks = extension.create_environment_hooks(prefix_path, 'pkg_name')
            assert len(hooks) == 2
