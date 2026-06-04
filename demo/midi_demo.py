#!/usr/bin/env python3
"""Demo: run the MIDI melody extraction pipeline on a local .mid file.

Usage
-----
    python demo/midi_demo.py <path/to/file.mid> [artist] [title]

Example
-------
    python demo/midi_demo.py /tmp/imagine.mid "John Lennon" "Imagine"

The demo prints:
  1. Metadata (tempo, time signature, track list)
  2. The singability spec in compact LLM-prompt-block format
  3. The first 3 lines as raw JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the package is importable when run from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from midi_melody.loader import MidiLoader
from midi_melody.extractor import MelodyExtractor
from midi_melody.segmenter import PhraseSegmenter
from midi_melody.analyser import NoteAnalyser
from midi_melody.spec import LineSpec, SingabilitySpec


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python demo/midi_demo.py <file.mid> [artist] [title]", file=sys.stderr)
        return 1

    midi_path = Path(sys.argv[1])
    artist = sys.argv[2] if len(sys.argv) > 2 else "Unknown Artist"
    title = sys.argv[3] if len(sys.argv) > 3 else midi_path.stem

    if not midi_path.exists():
        print(f"File not found: {midi_path}", file=sys.stderr)
        return 1

    # ---- 1. Load --------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  MIDI Melody Extraction Demo")
    print(f"  File   : {midi_path.name}")
    print(f"  Artist : {artist}")
    print(f"  Title  : {title}")
    print(f"{'='*60}\n")

    loader = MidiLoader(midi_path)
    tempo = loader.get_tempo()
    time_sig = loader.get_time_signature()
    tracks = loader.get_all_tracks()

    print(f"Tempo          : {tempo:.1f} BPM")
    print(f"Time signature : {time_sig[0]}/{time_sig[1]}")
    print(f"Tracks ({len(tracks)}):")
    for i, t in enumerate(tracks):
        note_count = len(t.notes)
        drum_flag = " [DRUM]" if t.is_drum else ""
        print(f"  [{i}] {t.name!r:20s}  {note_count:4d} notes{drum_flag}")

    # ---- 2. Extract melody ---------------------------------------------
    print()
    extractor = MelodyExtractor(loader)
    melody_notes = extractor.extract()
    print(f"Melody notes extracted : {len(melody_notes)}")

    # ---- 3. Segment into phrases ----------------------------------------
    segmenter = PhraseSegmenter(gap_threshold_beats=1.0)
    phrases = segmenter.segment(melody_notes, tempo)
    print(f"Phrases (lyric lines)  : {len(phrases)}")

    # ---- 4. Analyse notes -----------------------------------------------
    analyser = NoteAnalyser(time_signature=time_sig)
    line_specs: list[LineSpec] = []
    for idx, phrase in enumerate(phrases):
        note_specs = analyser.analyse(phrase, tempo)
        is_last = idx == len(phrases) - 1
        line_specs.append(
            LineSpec(
                line_index=idx,
                syllable_count=len(note_specs),
                notes=tuple(note_specs),
                phrase_boundary_after=not is_last,
            )
        )

    # ---- 5. Assemble spec -----------------------------------------------
    spec = SingabilitySpec(
        artist=artist,
        title=title,
        tempo_bpm=tempo,
        time_signature=time_sig,
        lines=line_specs,
    )

    # ---- 6. Print LLM prompt block (first 10 lines max) -----------------
    print(f"\n{'─'*60}")
    print("  LLM Prompt Block (first 10 lines):")
    print(f"{'─'*60}")
    limited_spec = SingabilitySpec(
        artist=artist,
        title=title,
        tempo_bpm=tempo,
        time_signature=time_sig,
        lines=line_specs[:10],
    )
    print(limited_spec.to_llm_prompt_block())

    # ---- 7. Print first 3 lines as JSON ---------------------------------
    print(f"\n{'─'*60}")
    print("  First 3 lines (JSON):")
    print(f"{'─'*60}")
    sample = {"lines": [l.to_dict() for l in line_specs[:3]]}
    print(json.dumps(sample, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
