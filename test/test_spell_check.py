# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from tempfile import TemporaryDirectory

from pylint.lint import Run
import pytest


spell_check_words_path = Path(__file__).parent / 'spell_check.words'


def test_spell_check():
    try:
        run_spell_check()
    except SystemExit as e:
        assert not e.code, 'Some spell checking errors'
    else:
        assert False, \
            'The pylint API is supposed to raise a SystemExit' \
            # pragma: no cover


def run_spell_check(store_unknown_words_path=None):
    global spell_check_words_path

    try:
        import enchant  # noqa: F401
    except ImportError:  # pragma: no cover
        pytest.skip(
            "Skipping spell checking tests since 'enchant' was not found")

    args = [
        '--disable=all',
        '--enable=spelling',
        '--spelling-dict=en_US',
        '--ignore-comments=no',
        '--spelling-private-dict-file=' +
        str(
            spell_check_words_path
            if store_unknown_words_path is None else store_unknown_words_path),
    ]
    if store_unknown_words_path is not None:
        args.append('--spelling-store-unknown-words=y')
    args += [
        str(Path(__file__).parents[1] / 'colcon_core'),
    ] + [
        str(p) for p in
        (Path(__file__).parents[1] / 'test').glob('**/*.py')
    ]
    Run(args)


def test_spell_check_word_list_order():
    global spell_check_words_path
    known_words = spell_check_words_path.read_text().splitlines()
    assert known_words == sorted(known_words), \
        'The word list should be ordered alphabetically'


def test_spell_check_word_list_duplicates():
    global spell_check_words_path
    known_words = spell_check_words_path.read_text().splitlines()
    duplicates = list(known_words)
    for word in set(known_words):
        duplicates.remove(word)
    known_words = spell_check_words_path.read_text().splitlines()
    assert len(duplicates) == 0, \
        'The word list should not contain duplicates'


# TODO use newer version of enchant on Travis CI
@pytest.mark.skip(
    reason='The older version of enchant on Travis CI / Trusty extracts less'
           'words from the sources so we cannot enforce an exact match atm')
def test_spell_check_word_list_unused():
    with TemporaryDirectory(prefix='test_colcon_') as basepath:
        words_path = Path(basepath) / 'words'
        try:
            run_spell_check(store_unknown_words_path=words_path)
        except SystemExit as e:
            assert not e.code, str(e)
        else:
            assert False, \
                'The pylint API is supposed to raise a SystemExit' \
                # pragma: no cover
        words = words_path.read_text().splitlines()

    global spell_check_words_path
    known_words = spell_check_words_path.read_text().splitlines()
    unused_words = set(known_words) - set(words)
    assert len(unused_words) == 0, \
        'The word list should not contain unused words'
