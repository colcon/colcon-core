# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import argparse

from colcon_core.argument_parser.destination_collector \
    import DestinationCollectorDecorator


def test_destination_collector_decorator():
    parser = argparse.ArgumentParser()
    decorator = DestinationCollectorDecorator(parser)
    assert decorator.get_destinations() == []

    decorator.add_argument('--option', action='store_true')
    assert decorator.get_destinations() == ['option']

    group = decorator.add_mutually_exclusive_group()
    group.add_argument('--other-option', action='store_true')
    assert decorator.get_destinations() == ['option', 'other_option']
