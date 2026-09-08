"""Find the offset between a set of lyric timings and the audio in hand.

Different uploads of the same song start at different moments, and a karaoke
file fetched from the internet was timed against some other copy. Trusting the
first line's timestamp is exactly what fails on a track that opens with several
seconds of near-silence, so instead we line the whole lyric up against where the
separated vocal actually starts making sound.

Two stages, and they measure different things on purpose. The coarse stage
cross-correlates the word onsets against the vocal's spectral flux: sharp
peaks, so it can tell one bar from the next, but late by around a tenth of a
second, because flux measures the ramp of an attack and not its start. The fine
stage then paints the lyric as the stretches it claims the singer is sounding
and slides that against where the voice actually is, within half a second of
the coarse answer. What makes that stage worth having is that it uses both
edges of every word -- where it starts and where it stops -- so the lag the
attack ramp adds at one end it takes back at the other.

Measured against the seeded songs, whose timings were hand-checked against
these very recordings, this lands within 20 ms on three of four and about
100 ms on the fourth; the same recording shifted by a known amount comes back
within 10 ms. Roughly a tenth of a second is the floor: separation bleed,
breath before a note and reverb after it all move where a vocal "starts".

An earlier version refined against peak-picked note onsets instead. That cannot
work: there are several times more detected onsets than sung words, so whatever
offset you propose has a note onset near it and the median distance to the
nearest one is near zero everywhere in the search. It could not correct the
coarse stage's bias because it could not see it.
"""
from __future__ import annotations

import numpy as np

from .audio import Voicing

SEARCH_BACK_S = 10.0
SEARCH_FORWARD_S = 30.0
FINE_WINDOW_S = 0.5
# Below this the lyric is sitting on silence and the answer means nothing.
MIN_AGREEMENT = 0.5


def _impulses(onsets: np.ndarray, n: int, hop: float) -> np.ndarray:
    imp = np.zeros(n, dtype=np.float32)
    for t in onsets:
        k = int(t / hop)
        if 0 <= k < n:
            imp[k] = 1.0
    return np.convolve(imp, np.hanning(11), mode="same")


def _claimed(spans: list[tuple[float, float]], n: int, hop: float) -> np.ndarray:
    """Where the lyric says the singer is sounding, as a 0/1 frame mask."""
    m = np.zeros(n, dtype=np.float32)
    for start, end in spans:
        i, j = int(start / hop), int(end / hop)
        if j > 0:
            m[max(0, i) : min(n, j)] = 1.0
    return m


def _peak(sig: np.ndarray, ref: np.ndarray, hop: float, lo: float, hi: float):
    """Lag in seconds that best lines `ref` up with `sig`, and how clear it is."""
    from scipy.signal import correlate

    a, b = sig - sig.mean(), ref - ref.mean()
    corr = correlate(a, b, mode="full", method="fft")
    lags = np.arange(-len(b) + 1, len(a)) * hop
    keep = (lags >= lo) & (lags <= hi)
    corr, lags = corr[keep], lags[keep]
    if not len(corr):
        return None, 0.0
    best = int(np.argmax(corr))
    far = np.abs(lags - lags[best]) > 1.0
    runner_up = float(corr[far].max()) if far.any() else 0.0
    ratio = float(corr[best]) / runner_up if runner_up > 0 else 0.0
    return float(lags[best]), ratio


def estimate(
    spans: list[tuple[float, float]], voicing: Voicing, duration: float
) -> tuple[float, bool]:
    """Return (seconds to add to the lyric times, whether we believe it)."""
    hop, n = voicing.hop, len(voicing.rms)
    spans = sorted((s, e) for s, e in spans if 0 <= s < duration and e > s)
    if len(spans) < 5 or n < 10:
        return 0.0, False

    onsets = np.asarray([s for s, _ in spans])
    coarse, ratio = _peak(voicing.flux, _impulses(onsets, n, hop), hop,
                          -SEARCH_BACK_S, SEARCH_FORWARD_S)
    if coarse is None:
        return 0.0, False

    activity = voicing.activity()
    claimed = _claimed(spans, n, hop)
    fine, _ = _peak(activity, claimed, hop,
                    coarse - FINE_WINDOW_S, coarse + FINE_WINDOW_S)
    best = fine if fine is not None else coarse

    # How much of what the lyric claims is sung actually is, once shifted. A
    # lyric lying over silence gets a confident-looking correlation peak and is
    # still in the wrong place.
    k = int(round(best / hop))
    lined_up = np.roll(claimed, k) > 0
    agreement = float(activity[lined_up].mean()) if lined_up.any() else 0.0
    return round(best, 3), bool(ratio > 1.15 and agreement >= MIN_AGREEMENT)


def shift(words, seconds: float):
    """Move every timed word by `seconds`, keeping the list order."""
    from .extract import TimedWord

    return [
        TimedWord(w.text, max(0.0, w.start + seconds), max(0.0, w.end + seconds),
                  w.line, w.confidence)
        for w in words
    ]
