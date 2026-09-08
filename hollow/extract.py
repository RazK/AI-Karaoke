"""Turn timed words into a HOLLOW representation, then throw the words away.

This is the only place in the system that sees a lyric and a clock at the same
time. It runs on this machine. What comes out the other side has no words in
it, and that is what everything downstream is allowed to see.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import prosody
from .audio import Voicing, semitones
from .format import HOLD_S, Hollow, Line, Slot, pairs_from_classes

# A line whose span is voiced less than this is a line the aligner has put
# somewhere the singer is not.
MIN_COVERAGE = 0.5
GROUP_GAP_S = 2.0


@dataclass
class TimedWord:
    text: str
    start: float
    end: float
    line: int
    confidence: float = 1.0


def _line_slots(
    line_words: list[TimedWord], voicing: Voicing | None, hard_limit: float
) -> tuple[list[Slot], float | None]:
    """Lay one line's words out as syllable slots, with the line's own pitch."""
    # Every syllable of the line, with the span of the word it came from.
    spans: list[tuple[prosody.Syl, float, float]] = []
    for w in line_words:
        syls = prosody.pronunciations(w.text)[0]
        step = (w.end - w.start) / len(syls)
        for i, s in enumerate(syls):
            spans.append((s, w.start + i * step, w.start + (i + 1) * step))

    slots: list[Slot] = []
    for i, (syl, t, nominal_end) in enumerate(spans):
        # How far the note could possibly run: to the next syllable, or, for the
        # last one, to the next line -- but never past the hard limit.
        limit = spans[i + 1][1] if i + 1 < len(spans) else hard_limit
        limit = max(limit, t + 0.02)
        if voicing is not None:
            sustain = voicing.offset_after(t, limit) - t
        else:
            sustain = min(nominal_end, limit) - t
        sustain = max(sustain, 0.02)
        # A slot is a held note only if the performance holds it open. A schwa
        # or a stop-closed syllable that measures long is the aligner running
        # past the end of the note, not a sustain.
        hold = sustain >= HOLD_S and syl.can_hold
        pitch = voicing.median_f0(t, t + sustain) if voicing is not None else None
        slots.append(Slot(round(t, 3), round(sustain, 3), syl.stressed, pitch, hold))

    # Melody, as semitones from the first pitched slot of the line. That slot's
    # own frequency goes back to the caller: without it every line reads as
    # starting at zero and the melodic relation between lines is lost.
    ref = next((s.pitch for s in slots if s.pitch), None)
    for s in slots:
        s.pitch = semitones(s.pitch, ref) if (s.pitch and ref) else None
    return slots, (round(ref, 1) if ref else None)


def _confidence(line_words: list[TimedWord], voicing: Voicing | None) -> float:
    """How much we believe this line is where the file says it is.

    Two things can go wrong. The aligner itself can be unsure of the words --
    which is what a held "oh-ee-oh-ee-oh" does to a transcriber. Or the line can
    be placed over a stretch where the voice is not sounding at all, which is
    what a karaoke file written against a different recording looks like.

    A syllable simply being long is not one of them: that is a held note, and
    the representation records it as one.
    """
    conf = min(w.confidence for w in line_words)
    if voicing is not None:
        cover = voicing.coverage(line_words[0].start, line_words[-1].end)
        if cover < MIN_COVERAGE:
            conf *= cover / MIN_COVERAGE
    return round(conf, 3)


def build(
    words: list[TimedWord],
    voicing: Voicing | None,
    *,
    song_ref: str,
    duration: float,
    source_kind: str,
    offset_ms: int = 0,
    offset_confident: bool = True,
    notes: dict | None = None,
) -> tuple[Hollow, list[str]]:
    """Build a HOLLOW file.

    Returns it together with the original line texts, which the caller keeps on
    this machine (the singability exam needs them, and nothing else does).
    """
    by_line: dict[int, list[TimedWord]] = {}
    for w in words:
        if w.text.strip():
            by_line.setdefault(w.line, []).append(w)
    order = sorted(by_line)
    texts = [" ".join(w.text for w in by_line[i]) for i in order]

    lines: list[Line] = []
    labels = prosody.rhyme_classes(texts)
    for k, i in enumerate(order):
        lw = sorted(by_line[i], key=lambda w: w.start)
        nxt = by_line[order[k + 1]][0].start if k + 1 < len(order) else duration
        limit = min(lw[-1].end + 2.0, nxt, duration)
        slots, ref_hz = _line_slots(lw, voicing, max(limit, lw[-1].start + 0.05))
        if not slots:
            continue
        lines.append(Line(len(lines), 0, slots, labels[k], _confidence(lw, voicing),
                          ref_hz))

    # Phrase groups: a gap in the singing starts a new one.
    groups: list[list[int]] = []
    for l in lines:
        if groups and l.start - lines[groups[-1][-1]].end <= GROUP_GAP_S:
            groups[-1].append(l.id)
        else:
            groups.append([l.id])
    for gi, ids in enumerate(groups):
        for lid in ids:
            lines[lid].group = gi

    h = Hollow(
        song_ref=song_ref,
        duration=round(duration, 3),
        lines=lines,
        groups=groups,
        rhyme_pairs=pairs_from_classes([l.rhyme for l in lines]),
        source_kind=source_kind,
        offset_ms=offset_ms,
        offset_confident=offset_confident,
        notes=notes or {},
    )
    return h, texts
