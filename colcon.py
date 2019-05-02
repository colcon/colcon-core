# Copyright 2019 Dan Rose, no rights reserved

# This module exists for multi-python environments
# so the user can invoke colcon as `python -m colcon`


if __name__ == '__main__':
    import colcon_core.command
    import sys

    sys.exit(colcon_core.command.main())
else:
    import warnings

    warnings.warn("This module is intended to be run as a main module. "
                  "Did you mean to import colcon-core instead?")
