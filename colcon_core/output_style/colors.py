# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from colcon_core.output_style import OutputStyleExtensionPoint
from colcon_core.output_style import Stylizer
from colcon_core.plugin_system import satisfies_version


class AnsiEscape(Stylizer):
    """ANSI text style modifier."""

    __slots__ = ()

    def __new__(cls, start, end=0):  # noqa: D102
        return super().__new__(cls, f'\033[{start}m', f'\033[{end}m')

    def __add__(self, other):  # noqa: D105
        if not isinstance(other, AnsiEscape):
            return super().__add__(other)
        return AnsiEscape(
            self._combine(self.start, other.start),
            self._combine(other.end, self.end))

    @staticmethod
    def _combine(first, second):
        first = first[2:-1]
        second = second[2:-1]
        if first == second:
            return first
        return f'{first};{second}'


AnsiEscape.Black = AnsiEscape(30)
AnsiEscape.Blue = AnsiEscape(34)
AnsiEscape.Bold = AnsiEscape(1, 22)
AnsiEscape.Cyan = AnsiEscape(36)
AnsiEscape.Faint = AnsiEscape(2, 22)
AnsiEscape.Flashing = AnsiEscape(5, 25)
AnsiEscape.Green = AnsiEscape(32)
AnsiEscape.Invert = AnsiEscape(7, 27)
AnsiEscape.Italic = AnsiEscape(3, 23)
AnsiEscape.Magenta = AnsiEscape(35)
AnsiEscape.Red = AnsiEscape(31)
AnsiEscape.Strike = AnsiEscape(9, 29)
AnsiEscape.Underline = AnsiEscape(4, 24)
AnsiEscape.White = AnsiEscape(37)
AnsiEscape.Yellow = AnsiEscape(33)


class ColorsOutputStyle(OutputStyleExtensionPoint):
    """Basic ANSI colorizing for console output."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            OutputStyleExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def apply_style(self, style):  # noqa: D102
        style.Critical = AnsiEscape(91)
        style.Error = AnsiEscape.Red
        style.PackageOrJobName = AnsiEscape.Italic + AnsiEscape.Blue
        style.SectionStart = AnsiEscape.Cyan
        style.SectionEnd = AnsiEscape.Magenta
        style.Strong = AnsiEscape.Bold
        style.Success = AnsiEscape.Green
        style.Warning = AnsiEscape.Yellow
        style.Weak = AnsiEscape.Faint
