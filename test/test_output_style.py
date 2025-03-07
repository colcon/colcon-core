# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import argparse
from io import StringIO
import runpy
from types import SimpleNamespace
from unittest.mock import patch

from colcon_core.output_style import __main__ as output_style_main
from colcon_core.output_style import add_output_style_arguments
from colcon_core.output_style import apply_output_style
from colcon_core.output_style import DEFAULT_OUTPUT_STYLE_ENVIRONMENT_VARIABLE
from colcon_core.output_style import OutputStyleExtensionPoint
from colcon_core.output_style import StyleCollection
from colcon_core.output_style import Stylizer
import pytest

from .extension_point_context import ExtensionPointContext


MarkdownBold = Stylizer('**', '**')
MarkdownItalic = Stylizer('_', '_')


class LoudErrors(OutputStyleExtensionPoint):

    def apply_style(self, style):
        style.Error = MarkdownBold


class SoftWarnings(OutputStyleExtensionPoint):

    PRIORITY = 90

    def apply_style(self, style):
        style.Warning = MarkdownItalic


def test_add_output_style_arguments():
    # No extensions available
    parser = argparse.ArgumentParser()
    with ExtensionPointContext():
        add_output_style_arguments(parser)

    # Secondary extensions are never the default
    parser = argparse.ArgumentParser()
    with ExtensionPointContext(
        soft_warnings=SoftWarnings,
    ):
        add_output_style_arguments(parser)

    assert parser.get_default('output_style') is None

    # Default extension selection
    parser = argparse.ArgumentParser()
    with ExtensionPointContext(
        loud_errors=LoudErrors,
        soft_warnings=SoftWarnings,
    ):
        add_output_style_arguments(parser)

    assert parser.get_default('output_style') == 'loud_errors'

    # Environment variable selection
    parser = argparse.ArgumentParser()
    with ExtensionPointContext(
        loud_errors=LoudErrors,
        soft_warnings=SoftWarnings,
    ):
        with patch.dict(
            'colcon_core.output_style.os.environ',
            {DEFAULT_OUTPUT_STYLE_ENVIRONMENT_VARIABLE.name: 'soft_warnings'},
        ):
            add_output_style_arguments(parser)

    assert parser.get_default('output_style') == 'soft_warnings'


@patch('colcon_core.output_style.Style')
def test_apply_output_style(mock_class):
    mock_class.Error = Stylizer.Default
    with ExtensionPointContext(
        loud_errors=LoudErrors,
        soft_warnings=SoftWarnings,
    ):
        apply_output_style(SimpleNamespace(output_style=None))
        assert mock_class.Error('foo') == 'foo'

        apply_output_style(SimpleNamespace(output_style='loud_errors'))
        assert mock_class.Error('foo') == '**foo**'

        apply_output_style(SimpleNamespace(output_style='soft_warnings'))
        assert mock_class.Warning('foo') == '_foo_'

    with ExtensionPointContext(
        unimplemented=OutputStyleExtensionPoint,
    ):
        with pytest.raises(NotImplementedError):
            apply_output_style(SimpleNamespace(output_style='unimplemented'))


def test_combine_stylizers():
    bold_and_italic = MarkdownBold + MarkdownItalic
    assert bold_and_italic('x') == '**_x_**'

    italic_and_bold = MarkdownItalic + MarkdownBold
    assert italic_and_bold('X') == '_**X**_'

    with pytest.raises(TypeError):
        MarkdownBold + 'x'


def test_style_default():
    style = StyleCollection()
    assert style.DoesNotExist == Stylizer.Default


@patch('sys.stdout', new_callable=StringIO)
def test_style_dump(mock_stdout):
    with ExtensionPointContext(
        loud_errors=LoudErrors,
        soft_warnings=SoftWarnings,
    ):
        runpy.run_path(output_style_main.__file__)

    stdout = mock_stdout.getvalue()
    assert 'loud_errors' in stdout
    assert 'soft_warnings' in stdout
