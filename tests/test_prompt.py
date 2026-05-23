import json
from pathlib import Path
import pytest
from generate.lrc import load_lrc
from generate.prompt import build_batch_prompt

FIXTURE = Path(__file__).parent / "fixtures" / "lrc_fixture.json"
CORPUS = (Path(__file__).parent / "fixtures" / "corpus_fixture.txt").read_text()


@pytest.fixture
def lines():
    data = json.loads(FIXTURE.read_text())
    return load_lrc(data)


def test_prompt_contains_title(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS)
    assert "Test Song" in prompt


def test_prompt_contains_artist(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS)
    assert "Test Artist" in prompt


def test_prompt_contains_corpus(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS)
    assert "Assemble" in prompt


def test_prompt_contains_syllable_counts(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS)
    # fixture lines: 6, 6, 8 syllables (pyphen: "real" → "re-al" = 2)
    assert "6 syllables" in prompt
    assert "8 syllables" in prompt


def test_prompt_contains_output_format(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS)
    assert "generated" in prompt
    assert "JSON array" in prompt


def test_error_hint_appended(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS, error_hint="count off on line 2")
    assert "count off on line 2" in prompt


def test_no_error_hint_by_default(lines):
    prompt = build_batch_prompt("Test Song", "Test Artist", lines, CORPUS)
    assert "PREVIOUS ATTEMPT FAILED" not in prompt
