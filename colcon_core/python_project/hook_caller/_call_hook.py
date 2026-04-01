# Copyright 2022 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from importlib import import_module
import os
import pickle
import sys


if __name__ == '__main__':
    backend_name, hook_name, child_in, child_out = sys.argv[1:]
    try:
        import msvcrt
    except ImportError:
        pass
    else:
        child_in = msvcrt.open_osfhandle(int(child_in), os.O_RDONLY)
        child_out = msvcrt.open_osfhandle(int(child_out), 0)
    if ':' in backend_name:
        backend_module_name, backend_object_name = backend_name.split(':', 2)
        backend_module = import_module(backend_module_name)
        backend = getattr(backend_module, backend_object_name)
    else:
        backend = import_module(backend_name)
    with os.fdopen(int(child_in), 'rb') as f:
        kwargs = pickle.load(f) or {}
    res = getattr(backend, hook_name)(**kwargs)
    with os.fdopen(int(child_out), 'wb') as f:
        pickle.dump(res, f)
