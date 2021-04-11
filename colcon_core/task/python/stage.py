# Copyright 2016-2018 Dirk Thomas
# Copyright 2021 Ruffin White
# Licensed under the Apache License, Version 2.0

from contextlib import suppress
# with suppress(ImportError):
#     # needed before importing distutils
#     # to avoid warning introduced in setuptools 49.2.0
#     import setuptools  # noqa: F401
# from distutils.sysconfig import get_python_lib
# import locale
import os
from pathlib import Path
# import shutil
# import sys
# from sys import executable

# from colcon_core.environment import create_environment_hooks
# from colcon_core.environment import create_environment_scripts
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
# from colcon_core.shell import create_environment_hook
# from colcon_core.shell import get_command_environment
# from colcon_core.subprocess import check_output
# from colcon_core.task import run
from colcon_core.task import TaskExtensionPoint
# from colcon_core.task.python import get_data_files_mapping
# from colcon_core.task.python import get_setup_data
from dirhash import dirhash

logger = colcon_logger.getChild(__name__)


class PythonStageTask(TaskExtensionPoint):
    """Stage Python packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(TaskExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    async def stage(self, *, additional_hooks=None):  # noqa: D102
        pkg = self.context.pkg
        args = self.context.args

        logger.info(
            "Staging Python package in '{args.path}'".format_map(locals()))

        # Use the number of CPU cores
        jobs = os.cpu_count()
        with suppress(AttributeError):
            # consider restricted set of CPUs if applicable
            jobs = min(jobs, len(os.sched_getaffinity(0)))
        if jobs is None:
            # the number of cores can't be determined
            jobs = 1

        # ignore all . files and . folders
        current_checksum = dirhash(args.path, 'md5', ignore=['.*'], jobs=jobs)

        # os.makedirs(args.build_base, exist_ok=True)
        stage_base = Path(args.build_base, 'stage')
        stage_base.mkdir(parents=True, exist_ok=True)
        current_path = Path(stage_base, 'colcon_stage_current.txt')
        previous_path = Path(stage_base, 'colcon_stage_previous.txt')

        current_path.write_text(str(current_checksum) + '\n')

        previous_checksum = None
        if previous_path.exists():
            previous_checksum = previous_path.read_text().rstrip()

        if args.tare_changes:
            previous_path.write_text(str(current_checksum) + '\n')
            return 0
        elif previous_checksum == current_checksum:
            return 0
        return 'changed'
