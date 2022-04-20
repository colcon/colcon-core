# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from pathlib import Path
import sysconfig


def get_python_install_path(name, vars=None):
    """
    Get Python install paths matching Colcon's preferred scheme.

    See sysconfig.get_path for more info about the arguments.

    :param name: Name of the path type
    :param vars: A dictionary of variables updating the values of
        sysconfig.get_config_vars()
    :rtype: Pathlib.Path
    """
    if not vars:
        vars = {}

    if hasattr(sysconfig, 'get_preferred_scheme'):
        # Python >= 3.10
        preferred_scheme = sysconfig.get_preferred_scheme('prefix')
    else:
        # Python < 3.10
        preferred_scheme = sysconfig._get_default_scheme()

    if 'deb_system' in sysconfig.get_scheme_names():
        # Ubuntu Jammy has a custom scheme
        preferred_scheme = 'deb_system'

    return Path(sysconfig.get_path(name, preferred_scheme, vars))
