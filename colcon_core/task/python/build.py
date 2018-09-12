# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from distutils.sysconfig import get_python_lib
import os
import re
import shutil
import sys
from sys import executable

from colcon_core.environment import create_environment_hooks
from colcon_core.environment import create_environment_scripts
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import get_command_environment
from colcon_core.task import check_call
from colcon_core.task import TaskExtensionPoint
from colcon_core.task.python import get_data_files_mapping
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

        # `setup.py egg_info` requires the --egg-base to exist
        os.makedirs(args.build_base, exist_ok=True)
        # `setup.py develop|install` requires the python lib path to exist
        python_lib = os.path.join(
            args.install_base, self._get_python_lib(args))
        os.makedirs(python_lib, exist_ok=True)
        # and being in the  PYTHONPATH
        env = dict(env)
        env['PYTHONPATH'] = python_lib + os.pathsep + \
            env.get('PYTHONPATH', '')

        if not args.symlink_install:
            rc = await self._undo_develop(pkg, args, env)
            if rc and rc.returncode:
                return rc.returncode

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
            cmd += [
                'bdist_egg', '--dist-dir', os.path.join(
                    args.build_base, 'dist'),
            ]
            rc = await check_call(self.context, cmd, cwd=args.path, env=env)
            if rc and rc.returncode:
                return rc.returncode

        else:
            self._undo_install(pkg, args, setup_py_data, python_lib)
            self._symlinks_in_build(args, setup_py_data)

            # invoke `setup.py develop` step in build space
            # to avoid placing any files in the source space
            cmd = [
                executable, 'setup.py',
                'develop', '--prefix', args.install_base,
                '--no-deps',
            ]
            if setup_py_data.get('data_files', []):
                cmd += ['install_data', '--install-dir', args.install_base]
            self._append_install_layout(args, cmd)
            rc = await check_call(
                self.context, cmd, cwd=args.build_base, env=env)
            if rc and rc.returncode:
                return rc.returncode

        hooks = create_environment_hooks(args.install_base, pkg.name)
        create_environment_scripts(
            pkg, args, default_hooks=hooks, additional_hooks=additional_hooks)

    async def _undo_develop(self, pkg, args, env):
        # undo previous develop if .egg-info is found and develop symlinks
        egg_info = os.path.join(
            args.build_base, '%s.egg-info' % pkg.name.replace('-', '_'))
        setup_py_build_space = os.path.join(args.build_base, 'setup.py')
        if os.path.exists(egg_info) and os.path.islink(setup_py_build_space):
            cmd = [
                executable, 'setup.py',
                'develop', '--prefix', args.install_base,
                '--uninstall',
            ]
            rc = await check_call(
                self.context, cmd, cwd=args.build_base, env=env)
            if rc:
                return rc

    def _undo_install(self, pkg, args, setup_py_data, python_lib):
        # undo previous install if install.log is found
        install_log = os.path.join(args.build_base, 'install.log')
        if not os.path.exists(install_log):
            return
        with open(install_log, 'r') as h:
            lines = [l.rstrip() for l in h.readlines()]

        packages = setup_py_data['packages']
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

        # remove entry from easy-install.pth file
        easy_install = os.path.join(
            args.install_base, self._get_python_lib(args),
            'easy-install.pth')
        if not os.path.exists(easy_install):
            return

        with open(easy_install, 'r') as h:
            content = h.read()
        pattern = r'^\./%s-\d.+\.egg\n' % re.escape(pkg.name)
        matches = re.findall(pattern, content, re.MULTILINE)
        if not matches:
            return

        assert len(matches) == 1, \
            "Multiple matching entries in '%s'" % easy_install
        content = content.replace(matches[0], '')
        with open(easy_install, 'w') as h:
            h.write(content)

    def _symlinks_in_build(self, args, setup_py_data):
        items = ['setup.py']
        # add setup.cfg if available
        if os.path.exists(os.path.join(args.path, 'setup.cfg')):
            items.append('setup.cfg')
        # add all first level packages
        items += list(filter(
            lambda name: '.' not in name, setup_py_data['packages']))
        # relative python-ish paths are allowed as entries in py_modules, see:
        # https://docs.python.org/3.5/distutils/setupscript.html#listing-individual-modules
        py_modules = setup_py_data.get('py_modules')
        if py_modules:
            py_modules_list = [
                p.replace('.', os.path.sep) + '.py' for p in py_modules]
            for py_module in py_modules_list:
                if not os.path.exists(os.path.join(args.path, py_module)):
                    raise RuntimeError(
                        "Provided py_modules '{py_module}' does not exist"
                        .format__map(locals()))
            items += py_modules_list
        data_files = get_data_files_mapping(
            setup_py_data.get('data_files', []))
        for source in data_files.keys():
            # work around data files incorrectly defined as not relative
            if os.path.isabs(source):
                source = os.path.relpath(source, args.path)
            items.append(source)

        # symlink files / directories from source space into build space
        for item in items:
            src = os.path.join(args.path, item)
            dst = os.path.join(args.build_base, item)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                if not os.path.islink(dst) or not os.path.samefile(src, dst):
                    if os.path.isfile(dst):
                        os.remove(dst)
                    elif os.path.isdir(dst):
                        shutil.rmtree(dst)
            if not os.path.exists(dst):
                os.symlink(src, dst)

    def _get_python_lib(self, args):
        path = get_python_lib(prefix=args.install_base)
        return os.path.relpath(path, start=args.install_base)

    def _append_install_layout(self, args, cmd):
        if 'dist-packages' in self._get_python_lib(args):
            cmd += ['--install-layout', 'deb']
