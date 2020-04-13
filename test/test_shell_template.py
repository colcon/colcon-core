# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from colcon_core.shell.template import expand_template
from em import TransientParseError
from mock import patch
import pytest


def test_expand_template():
    with TemporaryDirectory(prefix='test_colcon_') as base_path:
        template_path = Path(base_path) / 'template.em'
        destination_path = Path(base_path) / 'expanded_template'

        # invalid template, missing @[end if]
        template_path.write_text(
            '@[if True]')
        with pytest.raises(TransientParseError):
            with patch('colcon_core.shell.template.logger.error') as error:
                expand_template(template_path, destination_path, {})
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].endswith(
            " processing template '{template_path}'".format_map(locals()))
        assert not destination_path.exists()

        # missing variable
        template_path.write_text(
            '@(var)')
        with pytest.raises(NameError):
            with patch('colcon_core.shell.template.logger.error') as error:
                expand_template(template_path, destination_path, {})
        # the raised exception is catched and results in an error message
        assert error.call_count == 1
        assert len(error.call_args[0]) == 1
        assert error.call_args[0][0].endswith(
            " processing template '{template_path}'".format_map(locals()))
        assert not destination_path.exists()

        # skip all symlink tests on Windows for now
        if sys.platform == 'win32':  # pragma: no cover
            return

        # remove destination if it is a symlink
        destination_path.symlink_to(template_path)
        assert destination_path.is_symlink()
        expand_template(template_path, destination_path, {'var': 'value'})
        assert not destination_path.is_symlink()
        assert destination_path.exists()
