# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from colcon_core.package_identification import IgnoreLocationException
from colcon_core.package_identification.ignore import IGNORE_MARKER
from colcon_core.package_identification.ignore \
    import IgnorePackageIdentification
import pytest


def test_identify():
    extension = IgnorePackageIdentification()
    metadata = Mock()
    with TemporaryDirectory(prefix='test_colcon_') as basepath:
        metadata.path = Path(basepath)
        assert extension.identify(metadata) is None

        (metadata.path / IGNORE_MARKER).write_text('')
        with pytest.raises(IgnoreLocationException):
            extension.identify(metadata)
