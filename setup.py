# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import sys

from pkg_resources import parse_version
from setuptools import setup

minimum_version = '3.5'
if (
    parse_version('%d.%d' % (sys.version_info.major, sys.version_info.minor)) <
    parse_version(minimum_version)
):
    sys.exit('This package requires at least Python ' + minimum_version)

setup()
