# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_identification.python \
    import create_dependency_descriptor
from colcon_core.package_identification.python \
    PythonPackageIdentification
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
        dep = next(x for x in desc.dependencies['run'] if x == 'runA')
        assert dep.metadata['version_gt'] == '1.2.3'
        assert desc.dependencies['test'] == {'test'}

        assert callable(desc.metadata['get_python_setup_options'])
        options = desc.metadata['get_python_setup_options'](None)
        assert 'zip_safe' in options


def test_create_dependency_descriptor():
    eq_str = 'pkgname==2.2.0'
    dep = create_dependency_descriptor(eq_str)
    assert dep.metadata['version_eq'] == '2.2.0'

    lt_str = 'pkgname<2.3.0'
    dep = create_dependency_descriptor(lt_str)
    assert dep.metadata['version_lt'] == '2.3.0'

    lte_str = 'pkgname<=2.2.0'
    dep = create_dependency_descriptor(lte_str)
    assert dep.metadata['version_lte'] == '2.2.0'

    gt_str = 'pkgname>2.3.0'
    dep = create_dependency_descriptor(gt_str)
    assert dep.metadata['version_gt'] == '2.3.0'

    gte_str = 'pkgname>=2.2.0'
    dep = create_dependency_descriptor(gte_str)
    assert dep.metadata['version_gte'] == '2.2.0'

    neq_str = 'pkgname!=1.2.1'
    dep = create_dependency_descriptor(neq_str)
    assert dep.metadata['version_neq'] == '1.2.1'

    neq_str = 'pkgname~=1.4.1'
    dep = create_dependency_descriptor(neq_str)
    assert dep.metadata['version_compatible'] == '1.4.1'

    multi_str = 'pkgname<=3.2.0, >=2.2.0'
    dep = create_dependency_descriptor(multi_str)
    assert dep.metadata['version_gte'] == '2.2.0'
    assert dep.metadata['version_lte'] == '3.2.0'
