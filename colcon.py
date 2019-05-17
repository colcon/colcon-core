# Copyright 2019 Dan Rose, no rights reserved
# Licensed under the Apache License, Version 2.0

# This module exists for multi-Python environments
# so the user can invoke colcon as `python -m colcon`


if __name__ == '__main__':
    import colcon_core.command
    import sys

    sys.exit(colcon_core.command.main())
else:
    import warnings

    warnings.warn(
        'This module is intended to be run as a main module. '
        "Did you mean to import 'colcon_core' instead?")
