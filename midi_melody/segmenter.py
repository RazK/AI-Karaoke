"""PhraseSegmenter — splits a melody note list into phrase-level groups."""

from __future__ import annotations

import logging

import pretty_midi

logger = logging.getLogger(__name__)

_DEFAULT_GAP_THRESHOLD_BEATS = 1.0


class PhraseSegmenter:
    """Segments a flat list of melody notes into phrases (lyric lines).

    A phrase boundary is detected whenever the silence gap between the end
    of one note and the start of the next exceeds *gap_threshold_beats*.

    Parameters
    ----------
    gap_threshold_beats:
        Minimum silence (in beats) that triggers a phrase break.
        Default is ``1.0`` beat.
    """

    def __init__(
        self, gap_threshold_beats: float = _DEFAULT_GAP_THRESHOLD_BEATS
    ) -> None:
        self._gap_threshold_beats = gap_threshold_beats

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(
        self,
        notes: list[pretty_midi.Note],
        tempo: float,
    ) -> list[list[pretty_midi.Note]]:
        """Split *notes* into phrases based on inter-note silence gaps.

        Parameters
        ----------
        notes:
            Melody notes **sorted by start time**.
        tempo:
            Tempo in beats per minute, used to convert seconds to beats.

        Returns
        -------
        list[list[pretty_midi.Note]]
            Each inner list is one phrase.  Empty phrases are discarded.
        """
        if not notes:
            return []

        seconds_per_beat = 60.0 / tempo
        phrases: list[list[pretty_midi.Note]] = []
        current_phrase: list[pretty_midi.Note] = [notes[0]]

        for prev, curr in zip(notes, notes[1:]):
            gap_seconds = curr.start - prev.end
            gap_beats = gap_seconds / seconds_per_beat
            if gap_beats > self._gap_threshold_beats:
                phrases.append(current_phrase)
                current_phrase = []
            current_phrase.append(curr)

        if current_phrase:
            phrases.append(current_phrase)

        logger.debug(
            "Segmented %d notes into %d phrase(s) at %.2f-beat gap threshold",
            len(notes),
            len(phrases),
            self._gap_threshold_beats,
        )
        return phrases
