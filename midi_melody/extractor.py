"""MelodyExtractor — identifies and returns the melody track from a loaded MIDI."""

from __future__ import annotations

import logging
import statistics
from collections.abc import Sequence

import pretty_midi

from midi_melody import ExtractionError
from midi_melody.loader import MidiLoader

logger = logging.getLogger(__name__)

# Track names that are strong signals for a melody / vocal track
_MELODY_KEYWORDS = {"melody", "vocal", "voice", "lead", "vocals", "sing", "singer"}


class MelodyExtractor:
    """Extracts the melody / vocal track from a multi-track MIDI.

    The extraction strategy is applied in priority order:

    1. **Name match** — instrument name contains any of the melody keywords
       (case-insensitive).
    2. **Highest mean pitch** — non-percussion track whose notes have the
       highest average MIDI pitch number.
    3. **Highest note density in upper half** — non-percussion track with the
       most notes whose pitch is above the midpoint of all note pitches.

    Parameters
    ----------
    loader:
        A fully initialised :class:`~midi_melody.loader.MidiLoader`.
    """

    def __init__(self, loader: MidiLoader) -> None:
        self._loader = loader

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self) -> list[pretty_midi.Note]:
        """Return the melody notes sorted by start time.

        Returns
        -------
        list[pretty_midi.Note]
            All notes from the selected melody track, sorted chronologically.

        Raises
        ------
        ExtractionError
            If no suitable track can be found (e.g. the file has only
            percussion or empty tracks).
        """
        tracks = self._loader.get_all_tracks()
        melodic = [t for t in tracks if not t.is_drum and len(t.notes) > 0]
        if not melodic:
            raise ExtractionError(
                "No non-percussion tracks with notes found in the MIDI file."
            )

        # Strategy 1: name match
        track = self._by_name(melodic)
        if track is not None:
            logger.info("Melody track selected by name: '%s'", track.name)
            return sorted(track.notes, key=lambda n: n.start)

        # Strategy 2: highest mean pitch
        track = self._by_highest_mean_pitch(melodic)
        if track is not None:
            logger.info(
                "Melody track selected by highest mean pitch: '%s'", track.name
            )
            return sorted(track.notes, key=lambda n: n.start)

        # Strategy 3: highest note density in upper pitch range
        track = self._by_upper_density(melodic)
        if track is not None:
            logger.info(
                "Melody track selected by upper-range density: '%s'", track.name
            )
            return sorted(track.notes, key=lambda n: n.start)

        raise ExtractionError("Could not determine melody track using any strategy.")

    # ------------------------------------------------------------------
    # Extraction strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _by_name(
        tracks: list[pretty_midi.Instrument],
    ) -> pretty_midi.Instrument | None:
        """Return the first track whose name contains a melody keyword."""
        for track in tracks:
            name_lower = track.name.lower()
            if any(kw in name_lower for kw in _MELODY_KEYWORDS):
                return track
        return None

    @staticmethod
    def _by_highest_mean_pitch(
        tracks: list[pretty_midi.Instrument],
    ) -> pretty_midi.Instrument | None:
        """Return the non-percussion track with the highest average MIDI pitch."""
        best: pretty_midi.Instrument | None = None
        best_mean = -1.0
        for track in tracks:
            pitches = [n.pitch for n in track.notes]
            if not pitches:
                continue
            mean = statistics.mean(pitches)
            if mean > best_mean:
                best_mean = mean
                best = track
        return best

    @staticmethod
    def _by_upper_density(
        tracks: list[pretty_midi.Instrument],
    ) -> pretty_midi.Instrument | None:
        """Return the track with the most notes in the upper half of its pitch range."""
        best: pretty_midi.Instrument | None = None
        best_count = -1
        for track in tracks:
            pitches = [n.pitch for n in track.notes]
            if not pitches:
                continue
            midpoint = (min(pitches) + max(pitches)) / 2
            upper_count = sum(1 for p in pitches if p >= midpoint)
            if upper_count > best_count:
                best_count = upper_count
                best = track
        return best
