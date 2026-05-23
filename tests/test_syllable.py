import pytest
from generate.syllable import split_syllables, count_syllables


def test_single_syllable_words():
    assert count_syllables("is") == 1
    assert count_syllables("the") == 1
    assert count_syllables("life") == 1
    assert count_syllables("no") == 1


def test_multi_syllable_words():
    assert count_syllables("fantasy") == 3
    assert count_syllables("reality") == 4
    assert count_syllables("escape") == 2


def test_split_returns_list_of_strings():
    parts = split_syllables("fantasy")
    assert isinstance(parts, list)
    assert all(isinstance(s, str) for s in parts)
    assert len(parts) == 3


def test_split_joins_back_to_word():
    for word in ("fantasy", "reality", "escape", "life"):
        parts = split_syllables(word)
        assert "".join(parts).lower() == word.lower()


def test_punctuation_stripped():
    assert count_syllables("life,") == 1
    assert count_syllables('"Hurry,') == 2


def test_capitalization_preserved_on_first_syllable():
    parts = split_syllables("Fantasy")
    assert parts[0][0].isupper()


def test_contraction():
    assert count_syllables("it's") == 1


def test_count_matches_split_length():
    for word in ("bohemian", "rhapsody", "someone", "africa"):
        assert count_syllables(word) == len(split_syllables(word))
