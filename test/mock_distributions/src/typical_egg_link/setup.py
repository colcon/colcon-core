# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from setuptools import setup


setup(
    name='typical-egg-link',
    version='0.0.0',
    packages=[
        'typical_egg_link',
        'typical_egg_link_again',
    ],
    entry_points={
        'console_scripts': [
            'typical_egg_link = typical_egg_link:main',
        ],
    },
)
