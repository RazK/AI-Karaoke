"""What a HOLLOW file has to be true of, for every song in the library.

These are the acceptance tests. They run over the library rather than over a
fixture, so a song that only half-extracted cannot be quietly kept.
"""
from __future__ import annotations

import json

import pytest

from hollow import prosody
from hollow.exam import calibrate
from hollow.format import Hollow, leaks

# Nothing a singer does lasts this long on one syllable. A slot that claims to
# is the extractor measuring the instrumental break after the line.
MAX_SLOT_S = 3.0
LONG_GAP_S = 3.0


@pytest.fixture
def hollow(library, song) -> Hollow:
    return library.hollow(song.ref)


# ── the exam is calibrated on every song, every build ───────────────────────

def test_calibration_holds(library, song, hollow):
    original = library.originals(song.ref)
    cal = calibrate(hollow, original)
    assert cal.failures() == [], f"\n{cal}"


# ── the file carries no words ──────────────────────────────────────────────

def test_no_free_text(hollow):
    assert leaks(hollow) == []


def _vocabulary(obj) -> set[str]:
    """Every key and every string value anywhere in the file.

    Both are the format's own vocabulary rather than the song's: the keys are
    field names, and leaks() has already established that every string value is
    one of a handful of fixed schema constants.
    """
    if isinstance(obj, dict):
        return set(obj) | {w for v in obj.values() for w in _vocabulary(v)}
    if isinstance(obj, list):
        return {w for v in obj for w in _vocabulary(v)}
    return {obj} if isinstance(obj, str) else set()


def test_no_original_word_survives(library, song, hollow):
    """Stronger than leaks(): nothing else in the file spells a lyric word.

    The schema's own vocabulary comes out first -- replaced by a space, so that
    removing one token cannot join two halves into a third word -- and what is
    left is numbers. A word found in those would mean the timings themselves
    were carrying the lyric.
    """
    raw = json.dumps(hollow.to_dict()).lower()
    for token in _vocabulary(hollow.to_dict()) | {"true", "false", "null"}:
        raw = raw.replace(token.lower(), " ")

    found = sorted({
        w.lower()
        for line in library.originals(song.ref)
        for w in prosody.words(line)
        if len(w) >= 4 and w.lower() in raw
    })
    assert found == []


# ── the timings are a clock a player can follow ────────────────────────────

def test_slots_run_forwards(hollow):
    for line in hollow.lines:
        onsets = [s.t for s in line.slots]
        assert onsets == sorted(set(onsets)), f"line {line.id} slots out of order"
        for s in line.slots:
            assert s.sustain > 0, f"line {line.id} has a slot of no length"


def test_lines_do_not_overlap(hollow):
    for a, b in zip(hollow.lines, hollow.lines[1:]):
        assert a.end <= b.start + 1e-6, f"line {a.id} runs into line {b.id}"


def test_no_slot_sustains_past_its_line(hollow):
    """A sustain is a note being held, never the silence after it."""
    for a, b in zip(hollow.lines, hollow.lines[1:]):
        for s in a.slots:
            assert s.t + s.sustain <= b.start + 1e-6


def test_nothing_highlights_for_seconds(hollow):
    """The failure this catches: the last word of a line before an
    instrumental break lights up for the whole break."""
    for line in hollow.lines:
        for s in line.slots:
            assert s.sustain < MAX_SLOT_S, (
                f"line {line.id} holds one syllable for {s.sustain:.2f}s"
            )


def test_a_long_gap_is_left_empty(hollow):
    """Where the singing stops for seconds, the last slot does not fill it."""
    for a, b in zip(hollow.lines, hollow.lines[1:]):
        last = a.slots[-1]
        gap = b.start - last.t
        if gap >= LONG_GAP_S:
            assert last.sustain <= gap - 0.5, (
                f"line {a.id} ends on a {last.sustain:.2f}s note across a "
                f"{gap:.2f}s gap"
            )
