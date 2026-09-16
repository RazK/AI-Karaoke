"""What the dial is allowed to change, and what it is never allowed to change.

The one promise this project makes is that the rewrite is singable and keeps the
original's shape. The dial trades the source's own sentences against coherent
rephrasing -- and nothing else. These tests hold that line at every setting.

The writer here is a stub, not a model: a test that needed the API would cost
money, need a key, and prove nothing about the engine. The stub answers badly on
purpose, which is the interesting case -- it is the local verification and the
repair round that have to catch it.
"""
from __future__ import annotations

import re

import pytest

from hollow.dress import (QUOTE_END, REPHRASE_START, dress, ragged,
                          rewrite_share)
from hollow.exam import score
from hollow.format import MIN_SECTION_LINES

DIALS = [0.0, 0.6, 1.0]
CORPUS = ("data/datasets/ikea-manuals.txt", "data/datasets/yelp-reviews-1star.txt")


def stub_writer(answer_lines):
    """A writer that answers every row with a fixed phrase, right or wrong."""
    def ask(prompt: str) -> str:
        rows = re.findall(r"^L(\d+):.*<- write this one", prompt, re.M)
        if not rows:  # the repair round names its rows in the same way
            rows = re.findall(r"^L(\d+): you wrote", prompt, re.M)
        return "\n".join(f"L{r}: {answer_lines}" for r in rows)
    return ask


@pytest.fixture(scope="module")
def corpus_text():
    from pathlib import Path
    return Path(CORPUS[0]).read_text(encoding="utf-8")


# ── the dial itself ────────────────────────────────────────────────────────

def test_the_quote_end_asks_no_one_anything():
    assert rewrite_share(0.0) == 0.0
    assert rewrite_share(QUOTE_END) == 0.0


def test_the_rephrase_end_hands_over_everything():
    assert rewrite_share(REPHRASE_START) == 1.0
    assert rewrite_share(1.0) == 1.0


def test_the_dial_between_them_only_ever_rises():
    seen = [rewrite_share(x / 20) for x in range(21)]
    assert seen == sorted(seen)
    assert 0.0 < rewrite_share(0.5) < 1.0


# ── a line has to be a line ───────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "My wife's pasta had so much",        # the noun never arrives
    "Of my children fell asleep",         # the front is cut off
    "I have spent less on a full",
    "the steak was cold and",
])
def test_half_a_sentence_is_caught(text):
    assert ragged(text)


@pytest.mark.parametrize("text", [
    "And I'm gonna let you down",         # a song may open on "and"
    "The risotto tastes like paste",
    "Call the health board now",
])
def test_a_whole_thought_is_left_alone(text):
    assert ragged(text) == ""


# ── what never moves with the dial ────────────────────────────────────────

@pytest.mark.parametrize("licence", DIALS)
def test_the_tune_is_never_traded_for_words(library, song, licence, corpus_text):
    """Every line the exam scores has exactly the syllables the tune asks for."""
    h = library.hollow(song.ref)
    d = dress(h, corpus_text, licence, writer=stub_writer("tighten the bolt"),
              log=lambda *a: None)
    s = score(h, d.lines)
    assert s.fit == pytest.approx(1.0), (
        f"{song.title} at {licence}: fit {s.fit:.3f}, bends {len(d.bends)}")


@pytest.mark.parametrize("licence", DIALS)
def test_the_chorus_is_the_same_words_every_time(library, song, licence,
                                                 corpus_text):
    h = library.hollow(song.ref)
    d = dress(h, corpus_text, licence, writer=stub_writer("check every corner"),
              log=lambda *a: None)
    broken = [i for i, source in enumerate(d.echo_of)
              if source is not None and d.lines[i] != d.lines[source]]
    assert broken == [], f"{song.title} at {licence}: lines {broken} drifted"


def test_a_song_with_a_repeat_has_one(library):
    """The chorus rule cannot be silently absent from the whole library."""
    repeats = 0
    for s in library.songs():
        h = library.hollow(s.ref)
        repeats += sum(1 for e in h.section_echo if e is not None)
    assert repeats >= 3


# ── what does move with the dial ──────────────────────────────────────────

def test_the_dial_trades_the_source_s_own_words(library, corpus_text):
    song = library.songs()[0]
    h = library.hollow(song.ref)
    writer = stub_writer("hand-tighten only at this stage")
    quoted = dress(h, corpus_text, 0.0, writer=writer, log=lambda *a: None)
    written = dress(h, corpus_text, 1.0, writer=writer, log=lambda *a: None)
    assert sum(quoted.from_corpus) > sum(written.from_corpus) + 5


# ── sections are parts of a song, not leftovers ───────────────────────────

def test_sections_cover_every_line_exactly_once(library, song):
    h = library.hollow(song.ref)
    seen = [lid for ids in h.sections for lid in ids]
    assert sorted(seen) == list(range(len(h.lines)))
    assert len(seen) == len(set(seen))


def test_no_section_is_a_stub(library, song):
    h = library.hollow(song.ref)
    small = [ids for ids in h.sections if len(ids) < MIN_SECTION_LINES]
    # A short part is allowed only where it cannot be merged: between two
    # choruses, whose boundaries are real.
    assert all(len(ids) >= 2 for ids in small), \
        f"{song.title}: one-line sections {small}"
