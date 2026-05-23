import json
from pathlib import Path
import pytest
from generate.lrc import load_lrc, tokenize_line

FIXTURE = Path(__file__).parent / "fixtures" / "lrc_fixture.json"


@pytest.fixture
def lrc_data():
    return json.loads(FIXTURE.read_text())


def test_load_returns_correct_line_count(lrc_data):
    lines = load_lrc(lrc_data)
    assert len(lines) == 3


def test_start_ms(lrc_data):
    lines = load_lrc(lrc_data)
    assert lines[0].start_ms == 0
    assert lines[1].start_ms == 4000
    assert lines[2].start_ms == 8000


def test_original_is_list_of_word_arrays(lrc_data):
    lines = load_lrc(lrc_data)
    for line in lines:
        assert isinstance(line.original, list)
        for word in line.original:
            assert isinstance(word, list)
            assert all(isinstance(s, str) for s in word)


def test_word_count_matches_tokens(lrc_data):
    lines = load_lrc(lrc_data)
    # "Is this the real life" → 5 tokens → 5 word arrays
    assert len(lines[0].original) == 5


def test_syllable_counts(lrc_data):
    lines = load_lrc(lrc_data)
    # "Is this the real life" = 1+1+1+2+1 = 6 (pyphen: "real" → "re-al")
    assert lines[0].syllable_count == 6
    # "Is this just fantasy" = 1+1+1+3 = 6
    assert lines[1].syllable_count == 6
    # "No escape from reality" = 1+2+1+4 = 8
    assert lines[2].syllable_count == 8


def test_tokenize_hyphenated_word():
    tokens = tokenize_line("twelve-thirty flight")
    assert "twelve" in tokens
    assert "thirty" in tokens
    assert "flight" in tokens


def test_tokenize_strips_quotes():
    tokens = tokenize_line('"Hurry, boy"')
    assert any("Hurry" in t for t in tokens)
