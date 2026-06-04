"""Tests for PhraseSegmenter."""

from __future__ import annotations

import pretty_midi
import pytest

from midi_melody.segmenter import PhraseSegmenter


def _note(start: float, end: float, pitch: int = 60) -> pretty_midi.Note:
    return pretty_midi.Note(velocity=80, pitch=pitch, start=start, end=end)


TEMPO_120 = 120.0  # 0.5 seconds per beat


class TestPhraseSegmenterBasic:
    def test_empty_input_returns_empty(self) -> None:
        segmenter = PhraseSegmenter(gap_threshold_beats=1.0)
        assert segmenter.segment([], TEMPO_120) == []

    def test_single_note_is_one_phrase(self) -> None:
        notes = [_note(0.0, 0.4)]
        phrases = PhraseSegmenter().segment(notes, TEMPO_120)
        assert len(phrases) == 1
        assert len(phrases[0]) == 1

    def test_consecutive_notes_are_one_phrase(self) -> None:
        # Notes 0.1 s apart — gap = 0.1 s = 0.2 beats < 1.0
        notes = [_note(0.0, 0.4), _note(0.5, 0.9), _note(1.0, 1.4)]
        phrases = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, TEMPO_120)
        assert len(phrases) == 1
        assert len(phrases[0]) == 3


class TestPhraseSegmenterSplitting:
    def test_large_gap_splits_into_two_phrases(self) -> None:
        # At 120 BPM: 0.5 s = 1 beat.  Gap of 1.1 s = 2.2 beats > threshold 1.0
        notes = [
            _note(0.0, 0.4),
            _note(0.5, 0.9),
            # gap of 1.1 s ≈ 2.2 beats
            _note(2.0, 2.4),
            _note(2.5, 2.9),
        ]
        phrases = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, TEMPO_120)
        assert len(phrases) == 2
        assert len(phrases[0]) == 2
        assert len(phrases[1]) == 2

    def test_exact_threshold_does_not_split(self) -> None:
        # Gap of exactly 1.0 beat (0.5 s at 120 BPM) — should NOT split
        notes = [_note(0.0, 0.4), _note(0.9, 1.3)]
        # gap = 0.9 - 0.4 = 0.5 s = 1.0 beat — not strictly greater than threshold
        phrases = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, TEMPO_120)
        assert len(phrases) == 1

    def test_multiple_gaps_produce_multiple_phrases(self) -> None:
        # Three groups separated by 2-beat gaps
        notes = [
            _note(0.0, 0.4),
            _note(2.0, 2.4),  # gap 1.6 s = 3.2 beats
            _note(4.0, 4.4),  # gap 1.6 s = 3.2 beats
        ]
        phrases = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, TEMPO_120)
        assert len(phrases) == 3

    def test_custom_gap_threshold(self) -> None:
        # Same notes but with a 3-beat threshold — all stay together
        notes = [
            _note(0.0, 0.4),
            _note(2.0, 2.4),  # 3.2-beat gap
        ]
        phrases_tight = PhraseSegmenter(gap_threshold_beats=4.0).segment(notes, TEMPO_120)
        assert len(phrases_tight) == 1

        phrases_loose = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, TEMPO_120)
        assert len(phrases_loose) == 2


class TestPhraseSegmenterTempoScaling:
    def test_same_gap_at_different_tempos(self) -> None:
        # At 60 BPM: 1 beat = 1 s.  Gap of 0.6 s = 0.6 beats < 1.0 → no split.
        # At 120 BPM: gap of 0.6 s = 1.2 beats > 1.0 → split.
        notes = [_note(0.0, 0.4), _note(1.0, 1.4)]  # gap = 0.6 s

        phrases_60 = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, tempo=60.0)
        assert len(phrases_60) == 1

        phrases_120 = PhraseSegmenter(gap_threshold_beats=1.0).segment(notes, tempo=120.0)
        assert len(phrases_120) == 2
