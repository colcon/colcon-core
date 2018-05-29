# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import sys

from pkg_resources import parse_version
from setuptools import setup

minimum_version = '3.5'
if (
    parse_version('%d.%d' % (sys.version_info.major, sys.version_info.minor)) <
    parse_version(minimum_version)
):
    sys.exit('This package requires at least Python ' + minimum_version)

cmdclass = {}
try:
    from stdeb.command.sdist_dsc import sdist_dsc
except ImportError:
    pass
else:
    class CustomSdistDebCommand(sdist_dsc):
        """Weird approach to apply the Debian patches during packaging."""

        def run(self):  # noqa: D102
            from stdeb.command import sdist_dsc
            build_dsc = sdist_dsc.build_dsc

            def custom_build_dsc(*args, **kwargs):
                nonlocal build_dsc
                debinfo = self.get_debinfo()
                repackaged_dirname = \
                    debinfo.source + '-' + debinfo.upstream_version
                dst_directory = os.path.join(
                    self.dist_dir, repackaged_dirname, 'debian', 'patches')
                os.makedirs(dst_directory, exist_ok=True)
                # read patch
                with open('debian/patches/setup.cfg.patch', 'r') as h:
                    lines = h.read().splitlines()
                print(
                    "writing customized patch '%s'" %
                    os.path.join(dst_directory, 'setup.cfg.patch'))
                # write patch with modified path
                with open(
                    os.path.join(dst_directory, 'setup.cfg.patch'), 'w'
                ) as h:
                    for line in lines:
                        if line.startswith('--- ') or line.startswith('+++ '):
                            line = \
                                line[0:4] + repackaged_dirname + '/' + line[4:]
                        h.write(line + '\n')
                with open(os.path.join(dst_directory, 'series'), 'w') as h:
                    h.write('setup.cfg.patch\n')
                return build_dsc(*args, **kwargs)

            sdist_dsc.build_dsc = custom_build_dsc
            super().run()
    cmdclass['sdist_dsc'] = CustomSdistDebCommand

setup(cmdclass=cmdclass)
