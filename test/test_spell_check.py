# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path

import pytest
import scspell
from scspell import CorporaFile
from scspell import find_dict_file
from scspell import SCSPELL_BUILTIN_DICT
from scspell import spell_check_file


spell_check_words_path = Path(__file__).parent / 'spell_check.words'


@pytest.fixture(scope='module')
def known_words():
    global spell_check_words_path
    return spell_check_words_path.read_text().splitlines()


def test_spell_check(known_words):
    source_filenames = [Path(__file__).parents[1] / 'bin' / 'colcon'] + \
        list((Path(__file__).parents[1] / 'colcon-core').glob('**/*.py')) + \
        list((Path(__file__).parents[1] / 'test').glob('**/*.py'))

    found_known_words = set()
    unknown_words = set()

    # intercept failed check handling
    report_failed_check = scspell.report_failed_check

    def custom_report_failed_check(match_desc, filename, unmatched_subtokens):
        nonlocal found_known_words
        nonlocal known_words
        nonlocal report_failed_check
        nonlocal unknown_words
        for subtoken in list(unmatched_subtokens):
            if subtoken in known_words:
                found_known_words.add(subtoken)
                unmatched_subtokens.remove(subtoken)
                continue
        unknown_words |= set(unmatched_subtokens)

        if unmatched_subtokens:
            # call original function to report unmatched subtokens
            return report_failed_check(
                match_desc, filename, unmatched_subtokens)
        # otherwise just make the caller of the function happy
        return (
            match_desc.get_string(),
            match_desc.get_ofs() + len(match_desc.get_token()))

    scspell.report_failed_check = custom_report_failed_check

    # check all files
    with CorporaFile(
        find_dict_file(None), [SCSPELL_BUILTIN_DICT], None
    ) as dicts:
        dicts.register_extension('', 'Python')
        for source_path in source_filenames:
            ignores = set()
            report_only = True
            c_escapes = True
            # can't rely on the return value of the function
            # with the custom handling in place
            spell_check_file(
                str(source_path), dicts, ignores, report_only, c_escapes)

    unknown_word_count = len(unknown_words)
    assert unknown_word_count == 0, \
        'Found {unknown_word_count} unknown words: '.format_map(locals()) + \
        ', '.join(sorted(unknown_words))

    unused_known_words = set(known_words) - found_known_words
    unused_known_word_count = len(unused_known_words)
    assert unused_known_word_count == 0, \
        '{unused_known_word_count} words in the work list are not used: ' \
        .format_map(locals()) + ', '.join(sorted(unused_known_words))


def test_spell_check_word_list_order(known_words):
    assert known_words == sorted(known_words), \
        'The word list should be ordered alphabetically'


def test_spell_check_word_list_duplicates(known_words):
    assert len(known_words) == len(set(known_words)), \
        'The word list should not contain duplicates'
