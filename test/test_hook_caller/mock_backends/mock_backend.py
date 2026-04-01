# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

def build_wheel(
    wheel_directory, config_settings=None, metadata_directory=None
):
    return 'mock_wheel.whl'


def build_sdist(sdist_directory, config_settings=None):
    return 'mock_sdist.tar.gz'


def custom_hook(a, b=2):
    return a + b


def _private_hook():
    return 'hidden'
