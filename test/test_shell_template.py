# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory

from colcon_core.shell.template import expand_template
from em import TransientParseError
from mock import patch
import pytest


def test_expand_template():
    with TemporaryDirectory(prefix='test_colcon_') as destination_path:
        template_path = Path(destination_path) / 'invalid_template.em'

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
