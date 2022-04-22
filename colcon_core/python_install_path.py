# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from pathlib import Path
import sysconfig


def get_python_install_path(name, vars_=None):
    """
    Get Python install paths matching Colcon's preferred scheme.

    See sysconfig.get_path for more info about the arguments.

    :param name: Name of the path type
    :param vars_: A dictionary of variables updating the values of
        sysconfig.get_config_vars()
    :rtype: Pathlib.Path
    """
    kwargs = {}
    if vars_:
        kwargs['vars'] = vars_
    if 'deb_system' in sysconfig.get_scheme_names():
        kwargs['scheme'] = 'deb_system'
        
    return Path(sysconfig.get_path(name, **kwargs))
