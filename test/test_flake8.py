# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import logging
from pathlib import Path
import sys

from flake8 import LOG
from flake8.api.legacy import get_style_guide
from pydocstyle.utils import log


# avoid debug / info / warning messages from flake8 internals
LOG.setLevel(logging.ERROR)


def test_flake8():
    # for some reason the pydocstyle logger changes to an effective level of 1
    # set higher level to prevent the output to be flooded with debug messages
    log.setLevel(logging.WARNING)

    style_guide = get_style_guide(
        extend_ignore=['D100', 'D104'],
        show_source=True,
    )
    style_guide_tests = get_style_guide(
        extend_ignore=['D100', 'D101', 'D102', 'D103', 'D104', 'D105', 'D107'],
        show_source=True,
    )

    stdout = sys.stdout
    sys.stdout = sys.stderr
    # implicitly calls report_errors()
    report = style_guide.check_files([
        str(Path(__file__).parents[1] / 'bin' / 'colcon'),
        str(Path(__file__).parents[1] / 'colcon_core'),
    ])
    report_tests = style_guide_tests.check_files([
        str(Path(__file__).parents[1] / 'test'),
    ])
    sys.stdout = stdout

    total_errors = report.total_errors + report_tests.total_errors
    if total_errors:  # pragma: no cover
        # output summary with per-category counts
        print()
        if report.total_errors:
            report._application.formatter.show_statistics(report._stats)
        if report_tests.total_errors:
            report_tests._application.formatter.show_statistics(
                report_tests._stats)
        print(
            'flake8 reported {total_errors} errors'
            .format_map(locals()), file=sys.stderr)

    assert not total_errors, \
        'flake8 reported {total_errors} errors'.format_map(locals())
