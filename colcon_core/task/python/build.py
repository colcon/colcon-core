# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0
from distutils.sysconfig import get_python_lib
import os
from pathlib import Path
import shutil
import sys
from sys import executable

from colcon_core.environment import create_environment_hooks
from colcon_core.environment import create_environment_scripts
from colcon_core.logging import colcon_logger
from colcon_core.package_identification.python import get_setup_result
from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import get_command_environment
from colcon_core.task import check_call
from colcon_core.task import TaskExtensionPoint
from colcon_core.task.python import get_setup_data

logger = colcon_logger.getChild(__name__)


class PythonBuildTask(TaskExtensionPoint):
    """Build Python packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(TaskExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    async def build(self, *, additional_hooks=None):  # noqa: D102
        pkg = self.context.pkg
        args = self.context.args

        logger.info(
            "Building Python package in '{args.path}'".format_map(locals()))

        try:
            env = await get_command_environment(
                'setup_py', args.build_base, self.context.dependencies)
        except RuntimeError as e:
            logger.error(str(e))
            return 1
        setup_py_data = get_setup_data(self.context.pkg, env)

        try:
            shutil.rmtree(args.build_base)
        except FileNotFoundError:
            pass

        # `setup.py egg_info` requires the --egg-base to exist
        os.makedirs(args.build_base, exist_ok=True)
        # `setup.py` requires the python lib path to exist
        python_lib = os.path.join(
            args.install_base, self._get_python_lib(args))
        os.makedirs(python_lib, exist_ok=True)

        self._undo_install(pkg, args, setup_py_data, python_lib)

        if not args.symlink_install:
            # invoke `setup.py install` step with lots of arguments
            # to avoid placing any files in the source space
            cmd = [
                executable, 'setup.py',
                'egg_info', '--egg-base', args.build_base,
                'build', '--build-base', os.path.join(
                    args.build_base, 'build'),
                'install', '--prefix', args.install_base,
                '--record', os.path.join(args.build_base, 'install.log'),
                # prevent installation of dependencies specified in setup.py
                '--single-version-externally-managed',
            ]
            self._append_install_layout(args, cmd)
            completed_process = await check_call(
                self.context, cmd, cwd=args.path, env=env)
            if completed_process.returncode:
                return completed_process.returncode

        else:
            # invoke `setup.py` step in build space
            # to avoid placing any files in the source space

            # symlink *everything* from source space to build space
            for src_path in Path(args.path).iterdir():
                dst_path = Path(args.build_base, src_path.name)
                _clear_path(dst_path)
                dst_path.symlink_to(
                    src_path, target_is_directory=src_path.is_dir())

            cmd = [
                executable, 'setup.py',
                'build_py', '--build-lib', '.',
                'egg_info',
                'build_ext', '--inplace'
            ]
            if setup_py_data.get('data_files'):
                cmd += ['install_data', '--install-dir', args.install_base]

            # todo: We just ran setup.py. get_setup_result runs it again.
            #       We should use distutils.core.run_setup to get access to the
            #       distribution object
            setup_result = get_setup_result(
                Path(args.build_base, 'setup.py'), env=None)
            package_dir = Path(setup_result['package_dir'] or args.build_base)

            rc = await check_call(
                self.context, cmd, cwd=args.build_base, env=env)
            if rc and rc.returncode:
                return rc.returncode

            install_log = []

            # symlink *just Python modules* from build space to install space
            try:
                for src_path in _iter_modules(package_dir):
                    # Every package will have a top-level setup.py
                    # No need to install it.
                    if src_path == package_dir / 'setup.py':
                        continue
                    rel_path = src_path.relative_to(package_dir)
                    dst_path = Path(python_lib, rel_path)
                    if dst_path.exists():
                        logger.warning('Overwriting existing file at '
                                       + dst_path)
                        _clear_path(dst_path)
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    dst_path.symlink_to(src_path.resolve())
                    install_log.append(str(dst_path))
            finally:
                Path(args.build_base, 'install.log') \
                    .write_text('\n'.join(install_log))

        hooks = create_environment_hooks(args.install_base, pkg.name)
        create_environment_scripts(
            pkg, args, default_hooks=hooks, additional_hooks=additional_hooks)

    def _undo_install(self, pkg, args, setup_py_data, python_lib):
        # undo previous install if install.log is found
        install_log = os.path.join(args.build_base, 'install.log')
        if not os.path.exists(install_log):
            return
        with open(install_log, 'r') as h:
            lines = [l.rstrip() for l in h.readlines()]

        packages = setup_py_data.get('packages') or []
        for module_name in packages:
            if module_name in sys.modules:
                logger.warning(
                    "Switching to 'develop' for package '{pkg.name}' while it "
                    'is being used might result in import errors later'
                    .format_map(locals()))
                break

        # remove previously installed files
        directories = set()
        python_lib = python_lib + os.sep
        for line in lines:
            if not os.path.exists(line):
                continue
            if not line.startswith(python_lib):
                logger.debug(
                    'While undoing a previous installation files outside the '
                    'Python library path are being ignored: {line}'
                    .format_map(locals()))
                continue
            if not os.path.isdir(line):
                os.remove(line)
                # collect all parent directories until install base
                while True:
                    line = os.path.dirname(line)
                    if not line.startswith(python_lib):
                        break
                    directories.add(line)
        # remove empty directories
        for d in sorted(directories, reverse=True):
            try:
                os.rmdir(d)
            except OSError:
                pass
        os.remove(install_log)

    def _get_python_lib(self, args):
        path = get_python_lib(prefix=args.install_base)
        return os.path.relpath(path, start=args.install_base)

    def _append_install_layout(self, args, cmd):
        if 'dist-packages' in self._get_python_lib(args):
            cmd += ['--install-layout', 'deb']


def _clear_path(path):
    """Remove any file or directory at the given path."""
    try:
        os.unlink(str(path))
    except IsADirectoryError:
        shutil.rmtree(str(path))
    except FileNotFoundError:
        pass


def _iter_modules(base_path: Path):
    """Find all top-level modules (*/__init__.py or *.py) below base_path."""
    if (base_path / '__init__.py').resolve().is_file():
        yield base_path
        return

    for child in base_path.iterdir():
        if child.resolve().is_file() and child.suffix in ('.py', '.pyc'):
            yield child
        if child.resolve().is_dir():
            yield from _iter_modules(child)
