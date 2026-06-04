"""MidiLoader — loads a .mid file via pretty_midi and exposes track/tempo helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import pretty_midi

from midi_melody import MidiMelodyError

logger = logging.getLogger(__name__)


class MidiLoader:
    """Wraps :class:`pretty_midi.PrettyMIDI` and exposes convenience accessors.

    Parameters
    ----------
    midi_path:
        Path to the ``.mid`` file to load.

    Raises
    ------
    MidiMelodyError
        If the file cannot be parsed by ``pretty_midi``.
    """

    def __init__(self, midi_path: Path) -> None:
        self._midi_path = midi_path
        logger.debug("Loading MIDI: %s", midi_path)
        try:
            self._pm = pretty_midi.PrettyMIDI(str(midi_path))
        except Exception as exc:  # pretty_midi raises various exceptions
            raise MidiMelodyError(
                f"Failed to parse MIDI file '{midi_path}': {exc}"
            ) from exc
        logger.debug(
            "Loaded %d instruments from %s", len(self._pm.instruments), midi_path
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def pretty_midi(self) -> pretty_midi.PrettyMIDI:
        """The underlying :class:`pretty_midi.PrettyMIDI` object."""
        return self._pm

    def get_all_tracks(self) -> list[pretty_midi.Instrument]:
        """Return all instrument tracks in the MIDI file.

        Returns
        -------
        list[pretty_midi.Instrument]
            Tracks in the order they appear in the file.  May include
            percussion channels (``is_drum=True``).
        """
        return list(self._pm.instruments)

    def get_tempo(self) -> float:
        """Return the dominant (first) tempo in beats per minute.

        Returns
        -------
        float
            BPM of the first tempo change event, or 120.0 if none present.
        """
        tempo_change_times, tempos = self._pm.get_tempo_changes()
        if len(tempos) == 0:
            logger.warning("No tempo events found in %s; defaulting to 120 BPM", self._midi_path)
            return 120.0
        return float(tempos[0])

    def get_time_signature(self) -> tuple[int, int]:
        """Return the dominant (first) time signature as ``(numerator, denominator)``.

        Returns
        -------
        tuple[int, int]
            E.g. ``(4, 4)`` for common time.  Defaults to ``(4, 4)`` if no
            time signature events are present.
        """
        sigs = self._pm.time_signature_changes
        if not sigs:
            logger.warning(
                "No time signature events found in %s; defaulting to 4/4",
                self._midi_path,
            )
            return (4, 4)
        first = sigs[0]
        return (first.numerator, first.denominator)
