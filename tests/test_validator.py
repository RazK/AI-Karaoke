import pytest
from generate.lrc import AnnotatedLine
from generate.validator import validate_batch


def make_line(start_ms, text, original):
    return AnnotatedLine(start_ms=start_ms, text=text, original=original)


# --- valid cases ---

def test_valid_single_syllable_match():
    orig = [make_line(0, "Is this the real life", [["Is"], ["this"], ["the"], ["real"], ["life"]])]
    gen = [{"generated": [["Fix"], ["the"], ["shelf"], ["right"], ["now"]]}]
    result, err = validate_batch(orig, gen)
    assert result is not None and err is None
    assert result[0]["startMs"] == 0
    assert result[0]["original"] == orig[0].original
    assert result[0]["generated"] == gen[0]["generated"]


def test_valid_multi_syllable_word():
    orig = [make_line(0, "fantasy", [["fan", "ta", "sy"]])]
    gen = [{"generated": [["di", "a", "gram"]]}]
    result, err = validate_batch(orig, gen)
    assert result is not None and err is None


def test_valid_different_word_count():
    # 5 syllables orig (5 words) matched by 3 words with more syllables
    orig = [make_line(0, "test", [["Is"], ["this"], ["the"], ["real"], ["life"]])]
    gen = [{"generated": [["fan", "ta"], ["sy"], ["re", "al"]]}]  # 2+1+2 = 5
    result, err = validate_batch(orig, gen)
    assert result is not None


# --- invalid cases ---

def test_syllable_count_mismatch():
    orig = [make_line(0, "test", [["Is"], ["this"], ["the"], ["real"], ["life"]])]
    gen = [{"generated": [["Fix"], ["the"], ["shelf"]]}]  # 3, expected 5
    result, err = validate_batch(orig, gen)
    assert result is None
    assert "mismatch" in err


def test_wrong_line_count():
    orig = [make_line(0, "test", [["Is"]])]
    gen = []
    result, err = validate_batch(orig, gen)
    assert result is None
    assert "expected 1" in err


def test_missing_generated_field():
    orig = [make_line(0, "test", [["Is"]])]
    gen = [{"wrong": [["Is"]]}]
    result, err = validate_batch(orig, gen)
    assert result is None


def test_non_array_response():
    orig = [make_line(0, "test", [["Is"]])]
    result, err = validate_batch(orig, "not a list")
    assert result is None


def test_word_not_array_of_strings():
    orig = [make_line(0, "test", [["Is"]])]
    gen = [{"generated": ["Is"]}]  # word is a string, not list
    result, err = validate_batch(orig, gen)
    assert result is None
