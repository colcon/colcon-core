# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_identification.python \
    import PythonPackageIdentification
import pytest


def test_identify():
    extension = PythonPackageIdentification()

    with TemporaryDirectory(prefix='test_colcon_') as basepath:
        desc = PackageDescriptor(basepath)
        desc.type = 'other'
        assert extension.identify(desc) is None
        assert desc.name is None

        desc.type = None
        assert extension.identify(desc) is None
        assert desc.name is None
        assert desc.type is None

        basepath = Path(basepath)
        (basepath / 'setup.py').write_text('')
        assert extension.identify(desc) is None
        assert desc.name is None
        assert desc.type is None

        (basepath / 'setup.cfg').write_text('')
        assert extension.identify(desc) is None
        assert desc.name is None
        assert desc.type is None

        (basepath / 'setup.cfg').write_text(
            '[metadata]\n'
            'name = pkg-name\n')
        assert extension.identify(desc) is None
        assert desc.name == 'pkg-name'
        assert desc.type == 'python'

        desc.name = 'other-name'
        with pytest.raises(RuntimeError) as e:
            extension.identify(desc)
        assert str(e).endswith('Package name already set to different value')

        (basepath / 'setup.cfg').write_text(
            '[metadata]\n'
            'name = other-name\n'
            '[options]\n'
            'setup_requires =\n'
            "  build; sys_platform != 'win32'\n"
            "  build-windows; sys_platform == 'win32'\n"
            'install_requires =\n'
            '  runA > 1.2.3\n'
            '  runB\n'
            'tests_require = test == 2.0.0\n'
            'zip_safe = false\n')
        assert extension.identify(desc) is None
        assert desc.name == 'other-name'
        assert desc.type == 'python'
        assert set(desc.dependencies.keys()) == {'build', 'run', 'test'}
        assert desc.dependencies['build'] == {'build', 'build-windows'}
        assert desc.dependencies['run'] == {'runA', 'runB'}
        assert desc.dependencies['test'] == {'test'}

        assert callable(desc.metadata['get_python_setup_options'])
        options = desc.metadata['get_python_setup_options'](None)
        assert 'zip_safe' in options
