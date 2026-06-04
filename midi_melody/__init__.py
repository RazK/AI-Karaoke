"""midi_melody — MIDI melody extraction pipeline for singability spec generation."""

from __future__ import annotations


class MidiMelodyError(Exception):
    """Base exception for all midi_melody errors."""


class DownloadError(MidiMelodyError):
    """Raised when a MIDI file cannot be downloaded or located in the LMD index."""


class ExtractionError(MidiMelodyError):
    """Raised when melody extraction fails (e.g. no suitable track found)."""


__all__ = ["MidiMelodyError", "DownloadError", "ExtractionError"]
