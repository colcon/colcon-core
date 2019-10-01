# Copyright 2019 Rover Robotics via Dan Rose
# Licensed under the Apache License, Version 2.0

import distutils.core
import os


def run_setup_py(cwd: str, env: dict, script_args=(), stop_after='run'):
    """
    Modify the current process and run setup.py.

    This should be run in a subprocess so as not to dirty the state of the
    current process.

    :param cwd: Absolute path to a directory containing a setup.py script
    :param env: Environment variables to set before running setup.py
    :param script_args: command-line arguments to pass to setup.py
    :param stop_after: which
    :returns: The properties of a Distribution object, minus some useless
              and/or unpicklable properties
    """
    # need to be in setup.py's parent dir to detect any setup.cfg
    os.chdir(cwd)

    os.environ.clear()
    os.environ.update(env)

    result = distutils.core.run_setup(
        'setup.py', script_args=script_args, stop_after=stop_after)

    # could just return all attrs in result.__dict__, but we take this
    # opportunity to filter a few things that don't need to be there
    return {
        attr: value for attr, value in result.__dict__.items()
        if (
            # These *seem* useful but always have the value 0.
            # Look for their values in the 'metadata' object instead.
            attr not in result.display_option_names
            # Getter methods
            and not callable(value)
            # Private properties
            and not attr.startswith('_')
            # Objects that are generally not picklable
            and attr not in ('cmdclass', 'distclass', 'ext_modules')
        )
    }
