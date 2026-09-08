"""Take a spoken syllable apart and put it back together as a sung note.

WORLD (pyworld) decomposes speech into f0, a spectral envelope and an
aperiodicity map. The envelope is what makes the syllable the syllable; f0 and
duration are what make it speech rather than song. So we keep the envelope,
resample it onto the length HOLLOW asks for, throw the speaking pitch away and
substitute the melody, then resynthesise.

Stretching is not uniform. A slot that is held for two seconds holds its
*vowel* for two seconds; its consonants stay the length consonants are. So the
nucleus frames are stretched and the frames on either side are left alone.
"""
from __future__ import annotations

import numpy as np
import pyworld as pw

FP = 5.0  # ms per frame
MIN_CORE = 0.35  # a squeezed vowel may not fall below this much of itself


def analyse(a: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    f0, t = pw.harvest(a, sr, f0_floor=60.0, f0_ceil=900.0, frame_period=FP)
    f0 = pw.stonemask(a, f0, t, sr)
    sp = pw.cheaptrick(a, f0, t, sr)
    ap = pw.d4c(a, f0, t, sr)
    return f0, sp, ap


def time_map(n: int, i0: int, i1: int, m: int) -> np.ndarray:
    """Source frame index for each of `m` target frames.

    Frames [i0, i1) are the vowel and absorb the whole length change; if the
    note is too short even for the consonants, everything shrinks together.
    """
    i0 = max(0, min(i0, n - 1))
    i1 = max(i0 + 1, min(i1, n))
    head, core, tail = i0, i1 - i0, n - i1
    if m >= head + tail + max(1, int(core * MIN_CORE)):
        target_core = m - head - tail
        idx = np.concatenate([
            np.arange(head, dtype=float),
            i0 + np.linspace(0, core - 1e-6, target_core, endpoint=False),
            np.arange(i1, n, dtype=float),
        ])
        if target_core > core:
            # A frozen spectrum for a long hold sounds like a held organ key,
            # so drift a couple of frames back and forth across the vowel.
            k = np.arange(head, head + target_core)
            wob = 1.5 * np.sin(2 * np.pi * np.arange(target_core) / max(60.0, target_core / 2))
            idx[k] = np.clip(idx[k] + wob, i0, i1 - 1)
    else:
        idx = np.linspace(0, n - 1e-6, m, endpoint=False)
    return np.clip(idx, 0, n - 1)[:m]


def resynth(
    f0: np.ndarray,
    sp: np.ndarray,
    ap: np.ndarray,
    idx: np.ndarray,
    target_hz: np.ndarray,
    sr: int,
    core: tuple[int, int] | None = None,
) -> np.ndarray:
    """Rebuild the syllable on a new clock and a new melody.

    `core` is the vowel's frame range in the source. Speech creaks and trails
    off at the end of an utterance, and every syllable here *is* an utterance,
    so the vowel would otherwise fall out of voice halfway through a held note.
    Inside the core the note is made to keep singing.
    """
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(f0) - 1)
    w = (idx - lo)[:, None]
    spt = np.ascontiguousarray(sp[lo] * (1 - w) + sp[hi] * w)
    apt = np.ascontiguousarray(np.clip(ap[lo] * (1 - w) + ap[hi] * w, 0.0, 1.0))
    voiced = f0[lo] > 0
    if core is not None:
        c0, c1 = core
        inside = (idx >= c0) & (idx < c1)
        if inside.any() and voiced[inside].mean() > 0.5:
            voiced = voiced | inside
    f0t = np.where(voiced, target_hz[: len(idx)], 0.0)
    return pw.synthesize(np.ascontiguousarray(f0t), spt, apt, sr, FP)
