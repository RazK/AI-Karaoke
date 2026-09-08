"""From HOLLOW's semitones to actual frequencies, with a singer's inflections.

A slot says a whole number of semitones from the first pitched slot of its
line, and the line says where that slot sits in Hz. That is a score, not a
performance: a synthesiser that plays it literally sounds like a fax
machine. So each note gets an attack, a portamento into it when it is slurred
onto the last one, vibrato once it has been held long enough to earn one, and
a little drift.
"""
from __future__ import annotations

import numpy as np

from hollow.format import Line

# WORLD keeps the spectral envelope, so moving a note does not move the
# formants and the singer does not turn into a chipmunk. These are simply the
# bounds outside which the excitation stops sounding like a person at all.
NOTE_LO, NOTE_HI = 100.0, 800.0
COMFORT = 275.0  # where the middle of a song is put, if it is nowhere near it
# Beyond this, a jump is more likely the f0 tracker having slipped an octave
# than the singer having actually leapt one.
LEAP = 9


def repair_octaves(pitches: list[int | None], on: bool = True) -> list[int | None]:
    """Fold implausible octave leaps back in.

    HOLLOW does not say whether a +12 is a real octave or the extractor's f0
    tracker doubling; both look identical in the file. This assumes the melody
    is smooth and only moves a note when doing so removes a big leap.
    """
    if not on:
        return list(pitches)
    out = list(pitches)
    prev = next((p for p in out if p is not None), 0)
    for i, p in enumerate(out):
        if p is None:
            continue
        best = min((abs(p + 12 * k - prev), k) for k in (-2, -1, 0, 1, 2))
        if abs(p - prev) - best[0] > LEAP:
            out[i] = p + 12 * best[1]
        prev = out[i]
    return out


def line_hz(
    line: Line, ref_hz: float, *, repair: bool = True, octaves: int = 0
) -> list[float]:
    """Absolute frequency per slot.

    `octaves` is the one transposition the whole song shares -- moving lines
    independently would put an octave break between two lines that HOLLOW says
    are next to each other.
    """
    pitches = repair_octaves([s.pitch for s in line.slots], repair)
    last = 0
    filled = []
    for p in pitches:
        if p is None:
            p = last
        last = p
        filled.append(p)
    hz = [ref_hz * 2 ** (p / 12 + octaves) for p in filled]
    return [_in_range(f) for f in hz]


def _in_range(f: float) -> float:
    while f < NOTE_LO:
        f *= 2
    while f > NOTE_HI:
        f /= 2
    return f


def song_octaves(lines, refs: dict[int, float]) -> int:
    """One transposition for the whole song, from its own middle."""
    hz = [refs[l.id] * 2 ** ((s.pitch or 0) / 12)
          for l in lines if l.id in refs for s in l.slots]
    if not hz:
        return 0
    return int(round(np.log2(COMFORT / float(np.median(hz)))))


def contour(
    hz: float,
    dur: float,
    sr_frames: float,
    *,
    from_hz: float | None = None,
    vibrato_hz: float = 5.4,
    seed: int = 0,
) -> np.ndarray:
    """The frequency of one note, frame by frame.

    `from_hz` slurs in from the previous note; without it the note is attacked
    from just under pitch, which is what a singer does landing on a new phrase.
    """
    n = max(1, int(round(dur * 1000.0 / sr_frames)))
    t = np.arange(n) * sr_frames / 1000.0
    cents = np.zeros(n)

    # attack: portamento from the note before, or a short scoop from below
    if from_hz and from_hz > 0:
        glide = min(0.09, dur * 0.4)
        start = 1200 * np.log2(from_hz / hz)
        k = t < glide
        cents[k] += start * (1 - t[k] / glide) ** 2
    else:
        scoop = min(0.06, dur * 0.4)
        k = t < scoop
        cents[k] += -70 * (1 - t[k] / scoop) ** 2

    # vibrato, once the note has been held long enough to want one
    delay = 0.30
    if dur > delay + 0.15:
        depth = 34.0 * min(1.0, (dur - delay) / 0.6)
        ramp = np.clip((t - delay) / 0.35, 0, 1)
        cents += depth * ramp * np.sin(2 * np.pi * vibrato_hz * (t - delay))

    # pitch drift: slow, small, and different for every note
    rng = np.random.default_rng(seed)
    if n > 4:
        noise = rng.standard_normal(n)
        k = min(n, max(3, int(0.12 * 1000 / sr_frames)))
        kernel = np.hanning(k)
        kernel /= kernel.sum()
        cents += 9.0 * np.convolve(noise, kernel, mode="same")

    # a held note sags very slightly, the way a real breath does
    if dur > 1.0:
        cents -= 12.0 * np.clip((t - 1.0) / 2.0, 0, 1)

    return hz * 2 ** (cents / 1200.0)


def envelope(n: int, sr: int, *, attack: float = 0.014, release: float = 0.05) -> np.ndarray:
    """Fade a note in and out so notes butt together instead of clicking."""
    a = min(int(attack * sr), n // 3)
    r = min(int(release * sr), n // 3)
    e = np.ones(n)
    if a > 1:
        e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if r > 1:
        e[-r:] = np.cos(np.linspace(0, np.pi / 2, r)) ** 2
    return e
