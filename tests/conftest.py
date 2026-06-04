"""Shared pytest fixtures for midi_melody tests."""

from __future__ import annotations

from pathlib import Path

import pretty_midi
import pytest


# ---------------------------------------------------------------------------
# Helpers to build synthetic pretty_midi objects without reading a .mid file
# ---------------------------------------------------------------------------


def _make_note(
    pitch: int,
    start: float,
    end: float,
    velocity: int = 80,
) -> pretty_midi.Note:
    """Create a synthetic pretty_midi Note."""
    return pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)


def _make_instrument(
    name: str,
    notes: list[pretty_midi.Note],
    is_drum: bool = False,
    program: int = 0,
) -> pretty_midi.Instrument:
    inst = pretty_midi.Instrument(program=program, is_drum=is_drum, name=name)
    inst.notes.extend(notes)
    return inst


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def melody_notes_120bpm() -> list[pretty_midi.Note]:
    """Eight notes at 120 BPM (0.5 s/beat), one per beat, starting at beat 0.

    Beat positions (seconds): 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5
    Duration of each note: 0.4 s (just under one beat — not held)
    """
    notes = []
    for i in range(8):
        start = i * 0.5
        notes.append(_make_note(pitch=60 + i, start=start, end=start + 0.4))
    return notes


@pytest.fixture()
def fixture_midi_path(tmp_path: Path) -> Path:
    """Write a minimal but valid MIDI file to tmp_path and return its path.

    Structure:
    - Tempo: 120 BPM
    - Time signature: 4/4
    - Track 0: "melody" instrument with 6 notes forming two phrases
      (gap > 1 beat between note 3 and note 4)
    - Track 1: "bass" instrument with low-pitch notes
    """
    pm = pretty_midi.PrettyMIDI(initial_tempo=120.0)

    # Time signature 4/4
    pm.time_signature_changes.append(
        pretty_midi.TimeSignature(numerator=4, denominator=4, time=0.0)
    )

    # Melody track — 3 notes, gap, 3 more notes
    melody = pretty_midi.Instrument(program=0, name="melody")
    for i, (start, end, pitch) in enumerate([
        (0.0, 0.4, 64),   # E4
        (0.5, 0.9, 67),   # G4
        (1.0, 1.4, 69),   # A4
        # gap of 1.1 beats (0.55 s at 120 BPM) — triggers phrase break
        (2.0, 2.4, 72),   # C5
        (2.5, 2.9, 71),   # B4
        (3.0, 3.4, 69),   # A4
    ]):
        melody.notes.append(pretty_midi.Note(velocity=80, pitch=pitch, start=start, end=end))
    pm.instruments.append(melody)

    # Bass track — lower pitches
    bass = pretty_midi.Instrument(program=32, name="bass")
    for start in [0.0, 1.0, 2.0]:
        bass.notes.append(pretty_midi.Note(velocity=70, pitch=36, start=start, end=start + 0.4))
    pm.instruments.append(bass)

    path = tmp_path / "test_song.mid"
    pm.write(str(path))
    return path
