"""SingabilitySpec and LineSpec — song-level singability data model."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from midi_melody.analyser import NoteSpec

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LineSpec:
    """Singability descriptor for one phrase / lyric line.

    Attributes
    ----------
    line_index:
        Zero-based line number within the song.
    syllable_count:
        Number of notes (syllables) in the line.
    notes:
        Ordered list of :class:`~midi_melody.analyser.NoteSpec` objects.
    phrase_boundary_after:
        ``True`` if there is a significant breath pause after this line.
    """

    line_index: int
    syllable_count: int
    notes: tuple[NoteSpec, ...]
    phrase_boundary_after: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dictionary."""
        return {
            "line_index": self.line_index,
            "syllable_count": self.syllable_count,
            "notes": [n.to_dict() for n in self.notes],
            "phrase_boundary_after": self.phrase_boundary_after,
        }


@dataclass
class SingabilitySpec:
    """Full song-level singability specification.

    Attributes
    ----------
    artist:
        Artist name.
    title:
        Song title.
    tempo_bpm:
        Dominant tempo in beats per minute.
    time_signature:
        ``(numerator, denominator)`` tuple.
    lines:
        Ordered list of :class:`LineSpec` objects — one per phrase.
    """

    artist: str
    title: str
    tempo_bpm: float
    time_signature: tuple[int, int]
    lines: list[LineSpec] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dictionary of the full spec."""
        return {
            "artist": self.artist,
            "title": self.title,
            "tempo_bpm": round(self.tempo_bpm, 2),
            "time_signature": list(self.time_signature),
            "line_count": len(self.lines),
            "lines": [line.to_dict() for line in self.lines],
        }

    def save(self, output_path: Path) -> None:
        """Serialise the spec to a JSON file at *output_path*.

        Parameters
        ----------
        output_path:
            Destination path.  Parent directories are created as needed.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        logger.info("Singability spec saved to %s", output_path)

    def to_llm_prompt_block(self) -> str:
        """Format the spec as a compact text block for LLM prompt injection.

        The format is designed to let a lyric-generation model understand
        the melody structure — pitch, duration, stress, and phrasing —
        without exposing the original lyrics.

        Returns
        -------
        str
            A multi-line string, one note per line, with phrase breaks marked.

        Example
        -------
        ::

            Line 1 (8 syllables):
              syl 0: E4  0.5b  STRESSED
              syl 1: G4  0.25b
              syl 2: A4  1.0b  STRESSED HELD
            [PHRASE BREAK]
            Line 2 (6 syllables):
              syl 0: C4  0.5b  STRESSED
              ...
        """
        parts: list[str] = []
        for line in self.lines:
            parts.append(f"Line {line.line_index + 1} ({line.syllable_count} syllables):")
            for note in line.notes:
                flags = ""
                if note.is_stressed:
                    flags += "  STRESSED"
                if note.is_held:
                    flags += "  HELD"
                parts.append(
                    f"  syl {note.syllable_index}: {note.pitch}  {note.duration_beats}b{flags}"
                )
            if line.phrase_boundary_after:
                parts.append("[PHRASE BREAK]")
        return "\n".join(parts)
