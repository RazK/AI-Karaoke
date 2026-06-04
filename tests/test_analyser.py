"""Tests for NoteAnalyser and NoteSpec."""

from __future__ import annotations

import pretty_midi
import pytest

from midi_melody.analyser import NoteAnalyser, NoteSpec

TEMPO_120 = 120.0  # seconds_per_beat = 0.5


def _note(pitch: int, start: float, duration: float) -> pretty_midi.Note:
    return pretty_midi.Note(
        velocity=80, pitch=pitch, start=start, end=start + duration
    )


class TestNoteSpecDataclass:
    def test_frozen(self) -> None:
        spec = NoteSpec(
            syllable_index=0,
            pitch="C4",
            midi_note=60,
            duration_beats=0.5,
            is_stressed=True,
            is_held=False,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            spec.pitch = "D4"  # type: ignore[misc]

    def test_to_dict_keys(self) -> None:
        spec = NoteSpec(0, "E4", 64, 0.5, True, False)
        d = spec.to_dict()
        assert set(d.keys()) == {
            "syllable_index", "pitch", "midi_note",
            "duration_beats", "is_stressed", "is_held",
        }


class TestNoteAnalyserPitchName:
    def test_pitch_name_e4(self) -> None:
        analyser = NoteAnalyser()
        specs = analyser.analyse([_note(64, 0.0, 0.4)], TEMPO_120)
        assert specs[0].pitch == "E4"
        assert specs[0].midi_note == 64

    def test_pitch_name_c4(self) -> None:
        analyser = NoteAnalyser()
        specs = analyser.analyse([_note(60, 0.0, 0.4)], TEMPO_120)
        assert specs[0].pitch == "C4"


class TestNoteAnalyserDuration:
    def test_duration_in_beats_at_120bpm(self) -> None:
        # 0.5 s at 120 BPM = 1.0 beat
        analyser = NoteAnalyser()
        specs = analyser.analyse([_note(60, 0.0, 0.5)], TEMPO_120)
        assert specs[0].duration_beats == pytest.approx(1.0, rel=1e-3)

    def test_duration_in_beats_at_60bpm(self) -> None:
        # 0.5 s at 60 BPM = 0.5 beats
        analyser = NoteAnalyser()
        specs = analyser.analyse([_note(60, 0.0, 0.5)], tempo=60.0)
        assert specs[0].duration_beats == pytest.approx(0.5, rel=1e-3)


class TestNoteAnalyserHeld:
    def test_not_held_when_duration_le_one_beat(self) -> None:
        analyser = NoteAnalyser()
        # exactly 1 beat — NOT held (threshold is strictly >)
        specs = analyser.analyse([_note(60, 0.0, 0.5)], TEMPO_120)
        assert specs[0].is_held is False

    def test_held_when_duration_gt_one_beat(self) -> None:
        analyser = NoteAnalyser()
        # 1.1 beats at 120 BPM → 0.55 s
        specs = analyser.analyse([_note(60, 0.0, 0.55)], TEMPO_120)
        assert specs[0].is_held is True


class TestNoteAnalyserStress4_4:
    """Stress detection in 4/4 time (strong beats: 1 and 3, i.e. positions 0 and 2)."""

    def _analyser(self) -> NoteAnalyser:
        return NoteAnalyser(time_signature=(4, 4))

    def test_stressed_on_beat_1(self) -> None:
        # Beat 1 = position 0.0 beats → 0.0 s at any tempo
        specs = self._analyser().analyse([_note(60, 0.0, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is True

    def test_stressed_on_beat_3(self) -> None:
        # Beat 3 = position 2.0 beats → 1.0 s at 120 BPM
        specs = self._analyser().analyse([_note(60, 1.0, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is True

    def test_not_stressed_on_beat_2(self) -> None:
        # Beat 2 = position 1.0 beats → 0.5 s at 120 BPM
        specs = self._analyser().analyse([_note(60, 0.5, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is False

    def test_not_stressed_on_beat_4(self) -> None:
        # Beat 4 = position 3.0 beats → 1.5 s at 120 BPM
        specs = self._analyser().analyse([_note(60, 1.5, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is False

    def test_stressed_within_tolerance(self) -> None:
        # Start at 0.04 s = 0.08 beats off from beat 1 — within 0.1 tolerance
        specs = self._analyser().analyse([_note(60, 0.04, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is True

    def test_not_stressed_outside_tolerance(self) -> None:
        # Start at 0.1 s = 0.2 beats off from beat 1 — outside 0.1 tolerance
        specs = self._analyser().analyse([_note(60, 0.1, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is False


class TestNoteAnalyserStress3_4:
    """In 3/4 only beat 1 (position 0) is strong."""

    def _analyser(self) -> NoteAnalyser:
        return NoteAnalyser(time_signature=(3, 4))

    def test_stressed_on_beat_1(self) -> None:
        specs = self._analyser().analyse([_note(60, 0.0, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is True

    def test_not_stressed_on_beat_2_in_3_4(self) -> None:
        # Beat 2 in 3/4 = position 1.0 beat → 0.5 s
        specs = self._analyser().analyse([_note(60, 0.5, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is False

    def test_not_stressed_on_beat_3_in_3_4(self) -> None:
        # Beat 3 in 3/4 = position 2.0 beats → 1.0 s — NOT strong in 3/4
        specs = self._analyser().analyse([_note(60, 1.0, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is False


class TestNoteAnalyserStress6_8:
    """In 6/8 beats 1 and 4 (positions 0 and 3) are strong."""

    def _analyser(self) -> NoteAnalyser:
        return NoteAnalyser(time_signature=(6, 8))

    def test_stressed_on_beat_1(self) -> None:
        specs = self._analyser().analyse([_note(60, 0.0, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is True

    def test_stressed_on_beat_4(self) -> None:
        # Beat 4 in 6/8 = position 3.0 beats → 1.5 s at 120 BPM
        specs = self._analyser().analyse([_note(60, 1.5, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is True

    def test_not_stressed_on_beat_2_in_6_8(self) -> None:
        specs = self._analyser().analyse([_note(60, 0.5, 0.4)], TEMPO_120)
        assert specs[0].is_stressed is False


class TestNoteAnalyserSyllableIndex:
    def test_syllable_indices_are_sequential(self) -> None:
        notes = [_note(60 + i, i * 0.5, 0.4) for i in range(5)]
        specs = NoteAnalyser().analyse(notes, TEMPO_120)
        assert [s.syllable_index for s in specs] == list(range(5))

    def test_empty_phrase_returns_empty(self) -> None:
        assert NoteAnalyser().analyse([], TEMPO_120) == []
