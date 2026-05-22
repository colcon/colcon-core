# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from itertools import takewhile
from pathlib import Path

import pytest

pytest_version = tuple(
    int(x) for x in takewhile(str.isdigit, pytest.__version__.split('.'))
)

if pytest_version < (3, 9):
    @pytest.fixture
    def tmp_path(tmpdir):
        """
        Compatibility fixture for temporary directory allocation.

        This can be removed when we drop support for platforms with Pytest
        versions older than 3.9 (namely Enterprise Linux 8).
        """
        return Path(tmpdir)
