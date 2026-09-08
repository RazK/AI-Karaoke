"""Find the offset between a set of lyric timings and the audio in hand.

Different uploads of the same song start at different moments, and a karaoke
file fetched from the internet was timed against some other copy. Trusting the
first line's timestamp is exactly what fails on a track that opens with several
seconds of near-silence, so instead we line the whole lyric up against where the
separated vocal actually starts making sound.

Two stages. A coarse cross-correlation of every word onset against the vocal's
spectral flux finds the shift to within a note or so. Then a fine pass takes the
median distance from each shifted word onset to the nearest detected note onset,
which removes the tenth of a second the flux peak sits behind the attack.
"""
from __future__ import annotations

import numpy as np

from .audio import SR, Voicing

SEARCH_BACK_S = 10.0
SEARCH_FORWARD_S = 30.0
FINE_WINDOW_S = 0.25


def _impulses(onsets: np.ndarray, n: int, hop: float) -> np.ndarray:
    imp = np.zeros(n, dtype=np.float32)
    for t in onsets:
        k = int(t / hop)
        if 0 <= k < n:
            imp[k] = 1.0
    return np.convolve(imp, np.hanning(11), mode="same")


def estimate(
    onsets: list[float], voicing: Voicing, duration: float
) -> tuple[float, bool]:
    """Return (seconds to add to the lyric times, whether we believe it)."""
    from scipy.signal import correlate

    hop, n = voicing.hop, len(voicing.rms)
    onsets = np.asarray([t for t in onsets if 0 <= t < duration], dtype=np.float64)
    if len(onsets) < 5 or n < 10:
        return 0.0, False

    sig = voicing.flux - voicing.flux.mean()
    imp = _impulses(onsets, n, hop)
    imp = imp - imp.mean()
    corr = correlate(sig, imp, mode="full", method="fft")
    lags = np.arange(-len(imp) + 1, len(sig))
    keep = (lags >= -SEARCH_BACK_S / hop) & (lags <= SEARCH_FORWARD_S / hop)
    corr, lags = corr[keep], lags[keep]
    if not len(corr):
        return 0.0, False

    best = int(np.argmax(corr))
    coarse = float(lags[best] * hop)
    far = np.abs(lags - lags[best]) > 1.0 / hop
    runner_up = float(corr[far].max()) if far.any() else 0.0
    ratio = float(corr[best]) / runner_up if runner_up > 0 else 0.0

    # Fine pass: sit each shifted onset next to the nearest note the vocal
    # actually plays, and take the median disagreement.
    peaks = voicing.onset_times
    fine, matched = 0.0, 0
    if len(peaks):
        diffs = []
        for t in onsets + coarse:
            j = int(np.argmin(np.abs(peaks - t)))
            if abs(peaks[j] - t) < FINE_WINDOW_S:
                diffs.append(peaks[j] - t)
        matched = len(diffs)
        if matched >= max(8, 0.2 * len(onsets)):
            fine = float(np.median(diffs))

    confident = ratio > 1.15 and matched >= 0.2 * len(onsets)
    return round(coarse + fine, 3), bool(confident)


def shift(words, seconds: float):
    """Move every timed word by `seconds`, keeping the list order."""
    from .extract import TimedWord

    return [
        TimedWord(w.text, max(0.0, w.start + seconds), max(0.0, w.end + seconds),
                  w.line, w.confidence)
        for w in words
    ]
