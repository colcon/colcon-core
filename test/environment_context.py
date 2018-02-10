# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os


class EnvironmentContext:

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._memento = {}

    def __enter__(self):
        for k, v in self._kwargs.items():
            if k in os.environ:
                self._memento[k] = os.environ[k]
            os.environ[k] = v

    def __exit__(self, *_):
        for k, v in self._kwargs.items():
            if k in self._memento:
                os.environ[k] = self._memento[k]
            else:
                del os.environ[k]
