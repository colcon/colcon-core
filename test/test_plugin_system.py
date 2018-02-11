# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.plugin_system import get_first_line_doc
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_by_name
from colcon_core.plugin_system import order_extensions_by_priority
from colcon_core.plugin_system import order_extensions_grouped_by_priority
from colcon_core.plugin_system import satisfies_version
from colcon_core.plugin_system import SkipExtensionException
from mock import patch
import pytest

from .entry_point_context import EntryPointContext


def test_instantiate_extensions():
    class Extension1:
        pass

    class Extension2:
        pass

    with EntryPointContext(extension1=Extension1, extension2=Extension2):
        # successful instantiation of extensions
        extensions = instantiate_extensions('group')
        assert 'extension1' in extensions.keys()
        assert isinstance(extensions['extension1'], Extension1)
        assert 'extension2' in extensions.keys()
        assert isinstance(extensions['extension2'], Extension2)

        # unique extension instances
        unique_extensions = instantiate_extensions(
            'group', unique_instance=True)
        assert 'extension1' in unique_extensions.keys()
        assert isinstance(unique_extensions['extension1'], Extension1)
        assert extensions['extension1'] != unique_extensions['extension1']

        # exclude extension names
        extensions = instantiate_extensions(
            'group', exclude_names=['extension1'])
        assert 'extension1' not in extensions.keys()
        assert 'extension2' in extensions.keys()


def test_instantiate_extensions_exception():
    class ExtensionRaisingException:

        def __init__(self):
            raise Exception('extension raising exception')

    class ExtensionSkipExtensionException:

        def __init__(self):
            raise SkipExtensionException(
                'extension raising skip extension exception')

    with EntryPointContext(
        exception=ExtensionRaisingException,
        skip_extension_exception=ExtensionSkipExtensionException
    ):
        with patch('colcon_core.plugin_system.logger.error') as error:
            with patch('colcon_core.plugin_system.logger.info') as info:
                extensions = instantiate_extensions('group')

                # the entry point raising an exception different than a skip
                # extension exception results in an error message in the log
                assert error.call_count == 1
                assert len(error.call_args[0]) == 1
                assert "Exception instantiating extension 'group.exception'" \
                    in error.call_args[0][0]
                assert 'extension raising exception' in error.call_args[0][0]

                # the entry point raising a skip extension exception results in
                # an info message in the log
                assert info.call_count == 1
                assert len(info.call_args[0]) == 1
                assert "Skipping extension 'group.skip_extension_exception'" \
                    in info.call_args[0][0]
                assert 'extension raising skip extension exception' \
                    in info.call_args[0][0]
        # neither of the entry points was loaded successfully
        assert extensions == {}


class ExtensionA:
    PRIORITY = 100


class ExtensionB:
    PRIORITY = 100


class ExtensionC:
    PRIORITY = 110


def test_order_extensions_by_name():
    with EntryPointContext(foo=ExtensionA, bar=ExtensionB, baz=ExtensionC):
        extensions = instantiate_extensions('group')
    # ensure correct order based on name
    ordered_extensions = order_extensions_by_name(extensions)
    assert list(ordered_extensions.keys()) == ['bar', 'baz', 'foo']


def test_order_extensions_by_priority():
    with EntryPointContext(foo=ExtensionA, bar=ExtensionB, baz=ExtensionC):
        extensions = instantiate_extensions('group')
    # ensure correct order based on priority
    ordered_extensions = order_extensions_by_priority(extensions)
    assert list(ordered_extensions.keys()) == ['baz', 'bar', 'foo']


def test_order_extensions_grouped_by_priority():
    with EntryPointContext(foo=ExtensionA, bar=ExtensionB, baz=ExtensionC):
        extensions = instantiate_extensions('group')
    # ensure correct order based on priority
    grouped_extensions = order_extensions_grouped_by_priority(extensions)
    assert list(grouped_extensions.keys()) == [110, 100]
    # ensure correct order in each priority group based on name
    assert list(grouped_extensions[110].keys()) == ['baz']
    assert list(grouped_extensions[100].keys()) == ['bar', 'foo']


def test_get_first_line_doc():
    def single_line_doc():
        """Single line."""
    assert get_first_line_doc(single_line_doc) == 'Single line'

    def multi_line_doc():  # noqa: D400
        """
        First line

        Second line.
        """
    assert get_first_line_doc(multi_line_doc) == 'First line'

    def no_doc():
        pass  # pragma: no cover
    assert get_first_line_doc(no_doc) == ''

    def whitespace_doc():
        """ """
    assert get_first_line_doc(whitespace_doc) == ''

    def empty_lines_doc():
        """
        """
    assert get_first_line_doc(empty_lines_doc) == ''


def test_satisfies_version():
    satisfies_version('1.2.3', '^1')
    satisfies_version('1.2.3', '^1.1')

    with pytest.raises(RuntimeError) as e:
        satisfies_version('1.0.3', '^1.1')
    assert 'too old' in str(e)

    with pytest.raises(RuntimeError) as e:
        satisfies_version('2.0.0', '^1.2')
    assert 'newer' in str(e)

    # different semantic for version numbers before 1.0
    with pytest.raises(RuntimeError) as e:
        satisfies_version('0.2.3', '^0.1')
    assert 'newer' in str(e)
