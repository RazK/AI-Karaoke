"""Pipeline — top-level orchestrator for the MIDI melody extraction pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from midi_melody.analyser import NoteAnalyser
from midi_melody.downloader import LakhDownloader
from midi_melody.extractor import MelodyExtractor
from midi_melody.loader import MidiLoader
from midi_melody.segmenter import PhraseSegmenter
from midi_melody.spec import LineSpec, SingabilitySpec

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the full MIDI → singability spec pipeline.

    Call :meth:`run` to download a song, extract its melody, segment it
    into phrases, analyse note properties, and save the output JSON.

    Parameters
    ----------
    cache_dir:
        Directory used by :class:`~midi_melody.downloader.LakhDownloader`
        for caching the LMD index and downloaded MIDI files.
    gap_threshold_beats:
        Minimum silence gap (in beats) that triggers a phrase boundary.
        Forwarded to :class:`~midi_melody.segmenter.PhraseSegmenter`.
    """

    def __init__(
        self,
        cache_dir: Path = Path(".midi_cache"),
        gap_threshold_beats: float = 1.0,
    ) -> None:
        self._cache_dir = cache_dir
        self._gap_threshold_beats = gap_threshold_beats

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        artist: str,
        title: str,
        output_path: Path,
        midi_path: Path | None = None,
    ) -> SingabilitySpec:
        """Run the full pipeline and save the singability spec as JSON.

        Parameters
        ----------
        artist:
            Artist name (used for LMD lookup and spec metadata).
        title:
            Song title (used for LMD lookup and spec metadata).
        output_path:
            Path where the output JSON should be written.
        midi_path:
            Optional: supply a local ``.mid`` file directly, skipping the
            LMD download step.  Useful for testing or offline use.

        Returns
        -------
        SingabilitySpec
            The fully assembled singability spec.
        """
        # 1. Acquire the MIDI file
        if midi_path is None:
            logger.info("Downloading MIDI for '%s' – '%s' …", artist, title)
            downloader = LakhDownloader(cache_dir=self._cache_dir)
            midi_path = downloader.download(artist, title)
        else:
            logger.info("Using provided MIDI file: %s", midi_path)

        # 2. Load
        loader = MidiLoader(midi_path)
        tempo = loader.get_tempo()
        time_sig = loader.get_time_signature()
        logger.info("Tempo: %.1f BPM  Time sig: %d/%d", tempo, *time_sig)

        # 3. Extract melody
        extractor = MelodyExtractor(loader)
        melody_notes = extractor.extract()
        logger.info("Extracted %d melody notes", len(melody_notes))

        # 4. Segment into phrases
        segmenter = PhraseSegmenter(gap_threshold_beats=self._gap_threshold_beats)
        phrases = segmenter.segment(melody_notes, tempo)
        logger.info("Segmented into %d phrase(s)", len(phrases))

        # 5. Analyse each phrase
        analyser = NoteAnalyser(time_signature=time_sig)
        line_specs: list[LineSpec] = []
        for line_idx, phrase in enumerate(phrases):
            note_specs = analyser.analyse(phrase, tempo)
            is_last = line_idx == len(phrases) - 1
            line_specs.append(
                LineSpec(
                    line_index=line_idx,
                    syllable_count=len(note_specs),
                    notes=tuple(note_specs),
                    phrase_boundary_after=not is_last,
                )
            )

        # 6. Assemble the spec
        spec = SingabilitySpec(
            artist=artist,
            title=title,
            tempo_bpm=tempo,
            time_signature=time_sig,
            lines=line_specs,
        )

        # 7. Save
        spec.save(output_path)
        logger.info(
            "Pipeline complete: %d lines written to %s", len(line_specs), output_path
        )
        return spec
