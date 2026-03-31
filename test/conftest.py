# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from pathlib import Path

import pytest


if getattr(pytest, 'version_tuple', ()) < (3, 9):
    @pytest.fixture
    def tmp_path(tmpdir):
        """
        Compatibility fixture for temporary directory allocation.

        This can be removed when we drop support for platforms with Pytest
        versions older than 3.9 (namely Enterprise Linux 8).
        """
        return Path(tmpdir)
