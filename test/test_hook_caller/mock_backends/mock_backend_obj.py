# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

class Backend:

    def build_wheel(
        self, wheel_directory, config_settings=None, metadata_directory=None
    ):
        return 'mock_wheel.whl'

    def build_sdist(self, sdist_directory, config_settings=None):
        return 'mock_sdist.tar.gz'

    def custom_hook(self, a, b=2):
        return a + b


backend_instance = Backend()
