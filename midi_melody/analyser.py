"""NoteAnalyser — converts pretty_midi Note objects into NoteSpec dataclasses."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pretty_midi

logger = logging.getLogger(__name__)

# A note is considered "held" (melismatic) if its duration exceeds this many beats
_HELD_THRESHOLD_BEATS = 1.0

# Beat-alignment tolerance in beats (notes within this distance of a strong beat
# are marked as stressed)
_STRESS_TOLERANCE_BEATS = 0.1


@dataclass(frozen=True)
class NoteSpec:
    """Analysed descriptor for a single melody note / syllable.

    Attributes
    ----------
    syllable_index:
        Zero-based position of this note within its phrase.
    pitch:
        Scientific pitch notation string, e.g. ``"E4"``.
    midi_note:
        Raw MIDI pitch number (0–127).
    duration_beats:
        Duration of the note in beats.
    is_stressed:
        ``True`` if the note falls on a strong beat (beat 1 or 3 in 4/4)
        within the configured tolerance.
    is_held:
        ``True`` if ``duration_beats > 1.0`` (melismatic / sustained).
    """

    syllable_index: int
    pitch: str
    midi_note: int
    duration_beats: float
    is_stressed: bool
    is_held: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dictionary representation."""
        return {
            "syllable_index": self.syllable_index,
            "pitch": self.pitch,
            "midi_note": self.midi_note,
            "duration_beats": round(self.duration_beats, 4),
            "is_stressed": self.is_stressed,
            "is_held": self.is_held,
        }


class NoteAnalyser:
    """Analyses a phrase (list of notes) and returns :class:`NoteSpec` instances.

    Parameters
    ----------
    time_signature:
        ``(numerator, denominator)`` tuple, e.g. ``(4, 4)``.
    held_threshold_beats:
        Notes longer than this value are marked ``is_held=True``.
    stress_tolerance_beats:
        How close (in beats) a note's start must be to a strong beat to be
        considered stressed.
    """

    def __init__(
        self,
        time_signature: tuple[int, int] = (4, 4),
        held_threshold_beats: float = _HELD_THRESHOLD_BEATS,
        stress_tolerance_beats: float = _STRESS_TOLERANCE_BEATS,
    ) -> None:
        self._numerator, self._denominator = time_signature
        self._held_threshold = held_threshold_beats
        self._stress_tolerance = stress_tolerance_beats
        # Pre-compute strong beat positions (0-indexed within a bar)
        self._strong_beats = self._compute_strong_beats(
            self._numerator, self._denominator
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(
        self,
        phrase: list[pretty_midi.Note],
        tempo: float,
    ) -> list[NoteSpec]:
        """Analyse *phrase* and return a :class:`NoteSpec` for each note.

        Parameters
        ----------
        phrase:
            Notes in a single phrase, **sorted by start time**.
        tempo:
            Tempo in beats per minute.

        Returns
        -------
        list[NoteSpec]
            One entry per note, in the same order as *phrase*.
        """
        if not phrase:
            return []

        seconds_per_beat = 60.0 / tempo
        specs: list[NoteSpec] = []

        for idx, note in enumerate(phrase):
            pitch_name = pretty_midi.note_number_to_name(note.pitch)
            duration_beats = note.duration / seconds_per_beat
            beat_position = note.start / seconds_per_beat
            is_stressed = bool(self._is_on_strong_beat(beat_position))
            is_held = bool(duration_beats > self._held_threshold)

            specs.append(
                NoteSpec(
                    syllable_index=idx,
                    pitch=pitch_name,
                    midi_note=note.pitch,
                    duration_beats=round(duration_beats, 4),
                    is_stressed=is_stressed,
                    is_held=is_held,
                )
            )

        return specs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_strong_beats(numerator: int, denominator: int) -> list[float]:
        """Return 0-indexed strong beat positions for the given time signature.

        Rules (covers the most common meters):
        - Beat 0 (beat 1) is always strong.
        - 4/4, 4/2, 5/4 etc. (numerator ≥ 4): beat 2 (beat 3) is also strong.
        - 6/8, 6/4 (numerator = 6): beats 0 and 3 are strong.
        - 12/8 (numerator = 12): beats 0, 3, 6, 9 are strong.
        - 3/4, 3/8 (numerator = 3): only beat 0 is strong.
        """
        if numerator == 6:
            return [0.0, 3.0]
        if numerator == 12:
            return [0.0, 3.0, 6.0, 9.0]
        if numerator >= 4:
            return [0.0, 2.0]
        # 2/4, 2/2, 3/4, 3/8, etc. — only the downbeat
        return [0.0]

    def _is_on_strong_beat(self, beat_position: float) -> bool:
        """Return True if *beat_position* falls on a strong beat for this time signature.

        The position within the current bar is computed as
        ``beat_position % numerator``.  Strong beat positions are determined
        by :meth:`_compute_strong_beats` from the time signature passed at
        construction time.
        """
        position_in_bar = beat_position % self._numerator
        for strong_beat in self._strong_beats:
            if abs(position_in_bar - strong_beat) <= self._stress_tolerance:
                return True
        return False
