# Copyright 2016-2019 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path

import pytest

spell_check_words_path = Path(__file__).parent / 'spell_check.words'


@pytest.fixture(scope='module')
def known_words():
    global spell_check_words_path
    return spell_check_words_path.read_text().splitlines()


@pytest.mark.linter
def test_spell_check(known_words):
    from scspell import Report
    from scspell import SCSPELL_BUILTIN_DICT
    from scspell import spell_check

    source_filenames = [
        Path(__file__).parents[1] / 'bin' / 'colcon',
        Path(__file__).parents[1] / 'setup.py'] + \
        list((Path(__file__).parents[1] / 'colcon_core').glob('**/*.py')) + \
        list((Path(__file__).parents[1] / 'test').glob('**/*.py'))

    for source_filename in sorted(source_filenames):
        print('Spell checking:', source_filename)

    # check all files
    report = Report(known_words)
    spell_check(
        [str(p) for p in source_filenames], base_dicts=[SCSPELL_BUILTIN_DICT],
        report_only=report, additional_extensions=[('', 'Python')])

    unknown_word_count = len(report.unknown_words)
    assert unknown_word_count == 0, \
        f'Found {unknown_word_count} unknown words: ' + \
        ', '.join(sorted(report.unknown_words))

    unused_known_words = set(known_words) - report.found_known_words
    unused_known_word_count = len(unused_known_words)
    assert unused_known_word_count == 0, \
        f'{unused_known_word_count} words in the word list are not used: ' + \
        ', '.join(sorted(unused_known_words))


@pytest.mark.linter
def test_spell_check_word_list_order(known_words):
    assert known_words == sorted(known_words), \
        'The word list should be ordered alphabetically'


@pytest.mark.linter
def test_spell_check_word_list_duplicates(known_words):
    assert len(known_words) == len(set(known_words)), \
        'The word list should not contain duplicates'
