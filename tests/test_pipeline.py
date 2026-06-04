"""Integration test: full pipeline on a synthetic fixture MIDI (offline)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from midi_melody.pipeline import Pipeline
from midi_melody.spec import SingabilitySpec


class TestPipelineIntegration:
    """Run the full pipeline on the synthetic fixture MIDI.

    The fixture_midi_path fixture (defined in conftest.py) creates a minimal
    .mid file with two phrases separated by a > 1-beat gap, so we expect
    exactly 2 lines in the output spec.
    """

    def test_pipeline_produces_valid_spec(
        self, fixture_midi_path: Path, tmp_path: Path
    ) -> None:
        output_json = tmp_path / "spec.json"
        pipeline = Pipeline(gap_threshold_beats=1.0)
        spec = pipeline.run(
            artist="Test Artist",
            title="Test Song",
            output_path=output_json,
            midi_path=fixture_midi_path,
        )

        assert isinstance(spec, SingabilitySpec)
        assert spec.artist == "Test Artist"
        assert spec.title == "Test Song"
        assert spec.tempo_bpm > 0

    def test_pipeline_output_has_at_least_one_line(
        self, fixture_midi_path: Path, tmp_path: Path
    ) -> None:
        output_json = tmp_path / "spec.json"
        spec = Pipeline().run(
            artist="A", title="B", output_path=output_json, midi_path=fixture_midi_path
        )
        assert len(spec.lines) >= 1

    def test_pipeline_output_json_is_valid(
        self, fixture_midi_path: Path, tmp_path: Path
    ) -> None:
        output_json = tmp_path / "spec.json"
        Pipeline().run(
            artist="A", title="B", output_path=output_json, midi_path=fixture_midi_path
        )
        assert output_json.exists()
        data = json.loads(output_json.read_text())
        assert "lines" in data
        assert "tempo_bpm" in data
        assert "time_signature" in data

    def test_pipeline_notes_have_valid_pitch_and_duration(
        self, fixture_midi_path: Path, tmp_path: Path
    ) -> None:
        output_json = tmp_path / "spec.json"
        spec = Pipeline().run(
            artist="A", title="B", output_path=output_json, midi_path=fixture_midi_path
        )
        assert len(spec.lines) >= 1
        first_line = spec.lines[0]
        assert len(first_line.notes) >= 1
        note = first_line.notes[0]
        # Pitch must be a non-empty string like "E4"
        assert isinstance(note.pitch, str) and len(note.pitch) >= 2
        # Duration must be a positive number
        assert note.duration_beats > 0
        # midi_note in valid MIDI range
        assert 0 <= note.midi_note <= 127

    def test_pipeline_two_phrases_from_fixture(
        self, fixture_midi_path: Path, tmp_path: Path
    ) -> None:
        """The fixture MIDI has a > 1-beat gap at beat 3 → two phrases."""
        output_json = tmp_path / "spec.json"
        spec = Pipeline(gap_threshold_beats=1.0).run(
            artist="A", title="B", output_path=output_json, midi_path=fixture_midi_path
        )
        # The fixture has 3 melody notes, gap, 3 melody notes → 2 phrases
        assert len(spec.lines) == 2
        assert spec.lines[0].syllable_count == 3
        assert spec.lines[1].syllable_count == 3

    def test_to_llm_prompt_block_non_empty(
        self, fixture_midi_path: Path, tmp_path: Path
    ) -> None:
        output_json = tmp_path / "spec.json"
        spec = Pipeline().run(
            artist="A", title="B", output_path=output_json, midi_path=fixture_midi_path
        )
        block = spec.to_llm_prompt_block()
        assert "Line 1" in block
        assert "syl 0" in block
