# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from unittest.mock import Mock

from colcon_core.package_identification import IgnoreLocationException
from colcon_core.package_identification.ignore import IGNORE_MARKER
from colcon_core.package_identification.ignore \
    import IgnorePackageIdentification
import pytest


def test_identify(tmp_path):
    extension = IgnorePackageIdentification()
    metadata = Mock()
    metadata.path = tmp_path
    assert extension.identify(metadata) is None

    (metadata.path / IGNORE_MARKER).write_text('')
    with pytest.raises(IgnoreLocationException):
        extension.identify(metadata)
