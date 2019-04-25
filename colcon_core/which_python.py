# Copyright 2019 Dan Rose, no rights reserved
# Licensed under the Apache License, Version 2.0

from colcon_core.logging import colcon_logger
from colcon_core.environment_variable import EnvironmentVariable
import os
import shutil

logger = colcon_logger.getChild(__name__)

"""Environment variable to set the python executable"""
PYTHON_EXECUTABLE_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_PYTHON_EXECUTABLE',
    'Set the python executable (default: `which python3`)')


def which_python():
    """Get the python executable that packages should use"""
    python = os.getenv(PYTHON_EXECUTABLE_ENVIRONMENT_VARIABLE.name, '')
    if not python:
        python = shutil.which('python3')

    python = os.path.abspath(python)

    if not os.path.isfile(python):
        logger.warning('Python path does not exist: {}'.format(python))
    return python
