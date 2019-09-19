# Copyright 2016-2018 Dirk Thomas
# Copyright 2019 Rover Robotics
# Licensed under the Apache License, Version 2.0
import re

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_identification.python \
    import create_dependency_descriptor
from colcon_core.package_identification.python \
    import PythonPackageIdentification
import pytest


@pytest.fixture
def package_descriptor(tmp_path):
    """Create package descriptor and fail the test if its path changes."""
    desc = PackageDescriptor(tmp_path)
    yield desc
    assert str(desc.path) == str(tmp_path)


@pytest.fixture
def unchanged_empty_descriptor(package_descriptor):
    """Create package descriptor and fail the test if it changes."""
    yield package_descriptor
    assert package_descriptor.name is None
    assert package_descriptor.type is None


@pytest.mark.xfail
def test_error_in_setup_py(unchanged_empty_descriptor):
    setup_py = unchanged_empty_descriptor.path / 'setup.py'
    error_text = 'My hovercraft is full of eels'
    setup_py.write_text('raise OverflowError({!r})'.format(error_text))

    extension = PythonPackageIdentification()
    with pytest.raises(RuntimeError) as e:
        extension.identify(unchanged_empty_descriptor)

    assert e.match('Failure when trying to run setup script')
    assert e.match(re.escape(str(setup_py)))

    # details of the root cause should be in error string
    assert e.match('OverflowError')
    assert e.match(error_text)


def test_missing_setup_py(unchanged_empty_descriptor):
    extension = PythonPackageIdentification()
    # should not raise
    extension.identify(unchanged_empty_descriptor)


@pytest.mark.xfail
def test_empty_setup_py(unchanged_empty_descriptor):
    extension = PythonPackageIdentification()
    (unchanged_empty_descriptor.path / 'setup.py').write_text('')
    with pytest.raises(RuntimeError) as e:
        extension.identify(unchanged_empty_descriptor)
    assert e.match('not a Distutils setup script')


@pytest.mark.xfail
def test_setup_py_no_name(unchanged_empty_descriptor):
    extension = PythonPackageIdentification()
    (unchanged_empty_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup(name="")')
    with pytest.raises(RuntimeError):
        extension.identify(unchanged_empty_descriptor)


def test_re_identify_if_non_python_package(package_descriptor):
    package_descriptor.name = 'other-package'
    package_descriptor.type = 'other'
    extension = PythonPackageIdentification()
    extension.identify(package_descriptor)
    assert package_descriptor.name == 'other-package'
    assert package_descriptor.type == 'other'


def test_re_identify_python_if_same_python_package(package_descriptor):
    package_descriptor.name = 'my-package'
    package_descriptor.type = 'python'

    extension = PythonPackageIdentification()
    (package_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup(name="my-package")')

    extension.identify(package_descriptor)
    assert package_descriptor.name == 'my-package'
    assert package_descriptor.type == 'python'


@pytest.mark.xfail
def test_re_identify_python_if_different_python_package(package_descriptor):
    package_descriptor.name = 'other-package'
    package_descriptor.type = 'python'

    extension = PythonPackageIdentification()
    (package_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup(name="my-package")')

    with pytest.raises(RuntimeError):
        extension.identify(package_descriptor)

    assert package_descriptor.name == 'other-package'
    assert package_descriptor.type == 'python'


def test_minimal_cfg(package_descriptor):
    extension = PythonPackageIdentification()

    (package_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup()')
    (package_descriptor.path / 'setup.cfg').write_text(
        '[metadata]\nname = pkg-name')

    extension.identify(package_descriptor)

    # descriptor should be unchanged
    assert package_descriptor.name == 'pkg-name'
    assert package_descriptor.type == 'python'


def test_requires(package_descriptor):
    extension = PythonPackageIdentification()

    (package_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup()')

    (package_descriptor.path / 'setup.cfg').write_text(
        '[metadata]\n'
        'name = pkg-name\n'
        '[options]\n'
        'setup_requires =\n'
        '  setuptools; sys_platform != "imaginary_platform"\n'
        '  imaginary-package; sys_platform == "imaginary_platform"\n'
        'install_requires =\n'
        '  runA > 1.2.3\n'
        '  runB\n'
        'tests_require = test == 2.0.0\n'
        # prevent trying to look for setup_requires in the Package Index
        '[easy_install]\n'
        'allow_hosts = localhost\n')

    extension.identify(package_descriptor)
    assert package_descriptor.name == 'pkg-name'
    assert package_descriptor.type == 'python'
    assert package_descriptor.dependencies.keys() == {'build', 'run', 'test'}
    assert package_descriptor.dependencies == {
        'build': {'setuptools', 'imaginary-package'},
        'run':   {'runA', 'runB'},
        'test':  {'test'}
    }
    for dep in package_descriptor.dependencies['run']:
        if dep == 'runA':
            assert dep.metadata['version_gt'] == '1.2.3'

    assert package_descriptor.dependencies['run']
    assert package_descriptor.dependencies['run'] == {'runA', 'runB'}


def test_metadata_options(package_descriptor):
    (package_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup()')

    (package_descriptor.path / 'setup.cfg').write_text(
        '[metadata]\n'
        'name = pkg-name\n'
        '[options]\n'
        'zip_safe = false\n'
        'packages = find:\n')

    (package_descriptor.path / 'my_module').mkdir()
    (package_descriptor.path / 'my_module' / '__init__.py').touch()

    extension = PythonPackageIdentification()
    extension.identify(package_descriptor)

    options = package_descriptor.metadata['get_python_setup_options'](None)
    assert options['zip_safe'] is False
    assert options['packages'] == ['my_module']


@pytest.mark.xfail
def test_metadata_options_dynamic(package_descriptor):
    (package_descriptor.path / 'setup.py').write_text(
        'import setuptools; setuptools.setup()')
    (package_descriptor.path / 'version_helper.py').write_text(
        'import os; version = os.environ["version"]'
    )

    (package_descriptor.path / 'setup.cfg').write_text(
        '[metadata]\n'
        'name = my-package\n'
        'version = attr: version_helper.version\n'
    )

    extension = PythonPackageIdentification()
    extension.identify(package_descriptor)

    for version in ('1.0', '1.1'):
        options = package_descriptor.metadata['get_python_setup_options'](
            {'version': version})
        assert options['metadata'].version == version


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

    compat_str = 'pkgname~=1.4.1a4'
    dep = create_dependency_descriptor(compat_str)
    assert dep.metadata['version_gte'] == '1.4.1a4'
    assert dep.metadata['version_lt'] == '1.5'

    compat_str = 'pkgname~=1.4.1'
    dep = create_dependency_descriptor(compat_str)
    assert dep.metadata['version_gte'] == '1.4.1'
    assert dep.metadata['version_lt'] == '1.5'

    compat_str = 'pkgname~=1.4.1.4'
    dep = create_dependency_descriptor(compat_str)
    assert dep.metadata['version_gte'] == '1.4.1.4'
    assert dep.metadata['version_lt'] == '1.4.2'

    compat_str = 'pkgname~=11.12'
    dep = create_dependency_descriptor(compat_str)
    assert dep.metadata['version_gte'] == '11.12'
    assert dep.metadata['version_lt'] == '12.0'

    multi_str = 'pkgname<=3.2.0, >=2.2.0'
    dep = create_dependency_descriptor(multi_str)
    assert dep.metadata['version_gte'] == '2.2.0'
    assert dep.metadata['version_lte'] == '3.2.0'
