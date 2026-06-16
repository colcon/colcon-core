# Copyright 2023 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from importlib import import_module
import sys


if __name__ == '__main__':
    backend_name = sys.argv[1]
    if ':' in backend_name:
        backend_module_name, backend_object_name = backend_name.split(':', 2)
        backend_module = import_module(backend_module_name)
        backend = getattr(backend_module, backend_object_name)
    else:
        backend = import_module(backend_name)

    for attr in dir(backend):
        if callable(getattr(backend, attr)):
            print(attr)
