"""Tests for MelodyExtractor."""

from __future__ import annotations

import pytest
import pretty_midi

from midi_melody import ExtractionError
from midi_melody.extractor import MelodyExtractor
from midi_melody.loader import MidiLoader


def _make_note(pitch: int, start: float, end: float) -> pretty_midi.Note:
    return pretty_midi.Note(velocity=80, pitch=pitch, start=start, end=end)


def _make_instrument(
    name: str,
    pitches: list[int],
    is_drum: bool = False,
) -> pretty_midi.Instrument:
    inst = pretty_midi.Instrument(program=0, is_drum=is_drum, name=name)
    for i, p in enumerate(pitches):
        inst.notes.append(_make_note(p, start=float(i) * 0.5, end=float(i) * 0.5 + 0.4))
    return inst


class _FakeLoader:
    """Minimal stand-in for MidiLoader that serves pre-built instruments."""

    def __init__(self, instruments: list[pretty_midi.Instrument]) -> None:
        self._instruments = instruments

    def get_all_tracks(self) -> list[pretty_midi.Instrument]:
        return self._instruments


class TestMelodyExtractorByName:
    def test_picks_track_named_melody(self) -> None:
        low_pitch = _make_instrument("piano", [40, 41, 42])  # lower mean pitch
        vocal = _make_instrument("melody", [72, 74, 76])  # higher mean pitch but name wins
        loader = _FakeLoader([low_pitch, vocal])  # type: ignore[arg-type]
        extractor = MelodyExtractor(loader)  # type: ignore[arg-type]
        notes = extractor.extract()
        assert all(n.pitch in {72, 74, 76} for n in notes)

    def test_picks_track_named_vocal(self) -> None:
        other = _make_instrument("piano", [50, 51])
        vocal = _make_instrument("Vocals", [60, 61])
        loader = _FakeLoader([other, vocal])  # type: ignore[arg-type]
        notes = MelodyExtractor(loader).extract()  # type: ignore[arg-type]
        assert all(n.pitch in {60, 61} for n in notes)

    def test_name_match_is_case_insensitive(self) -> None:
        track = _make_instrument("LEAD GUITAR", [55, 57, 59])
        loader = _FakeLoader([track])  # type: ignore[arg-type]
        notes = MelodyExtractor(loader).extract()  # type: ignore[arg-type]
        assert len(notes) == 3


class TestMelodyExtractorByMeanPitch:
    def test_falls_back_to_highest_mean_pitch(self) -> None:
        low = _make_instrument("piano", [40, 42, 44])    # mean ≈ 42
        high = _make_instrument("strings", [70, 72, 74])  # mean ≈ 72
        loader = _FakeLoader([low, high])  # type: ignore[arg-type]
        notes = MelodyExtractor(loader).extract()  # type: ignore[arg-type]
        assert all(n.pitch in {70, 72, 74} for n in notes)


class TestMelodyExtractorErrors:
    def test_raises_when_all_tracks_are_drums(self) -> None:
        drum = _make_instrument("drums", [36, 38, 42], is_drum=True)
        loader = _FakeLoader([drum])  # type: ignore[arg-type]
        with pytest.raises(ExtractionError):
            MelodyExtractor(loader).extract()  # type: ignore[arg-type]

    def test_raises_when_all_tracks_are_empty(self) -> None:
        empty = _make_instrument("piano", [])
        loader = _FakeLoader([empty])  # type: ignore[arg-type]
        with pytest.raises(ExtractionError):
            MelodyExtractor(loader).extract()  # type: ignore[arg-type]

    def test_raises_when_no_tracks(self) -> None:
        loader = _FakeLoader([])  # type: ignore[arg-type]
        with pytest.raises(ExtractionError):
            MelodyExtractor(loader).extract()  # type: ignore[arg-type]


class TestMelodyExtractorNoteOrder:
    def test_notes_sorted_by_start_time(self) -> None:
        inst = _make_instrument("melody", [60, 62, 64, 65, 67])
        # Shuffle the notes to verify sorting
        inst.notes.reverse()
        loader = _FakeLoader([inst])  # type: ignore[arg-type]
        notes = MelodyExtractor(loader).extract()  # type: ignore[arg-type]
        starts = [n.start for n in notes]
        assert starts == sorted(starts)
