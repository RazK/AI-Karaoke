"""Backfilling `Line.ref_hz` when the representation does not carry it yet.

HOLLOW records pitch as semitones from the first slot of each line, which is
what a lyricist wants to read and is useless to a synthesiser on its own: it
says the shape of every line and never says where any of them sits. `ref_hz` is
the field that closes that gap. Until the extractor writes it, this measures it
the same way the extractor would -- from the song's own recording -- and caches
it in a sidecar next to the rendered audio, never inside the library.

Everything here is local: two files off the disk and an f0 tracker.
"""
from __future__ import annotations

import json
from pathlib import Path

import librosa
import numpy as np
import pyworld as pw

from hollow.format import Hollow

SR = 22050
FALLBACK_HZ = 220.0  # a comfortable tonic, when there is nothing to measure


def vocal_residual(mix_path: Path, inst_path: Path) -> tuple[np.ndarray, int]:
    """The mix minus its own instrumental, aligned and gain-matched.

    The two files are separate mp3s of the same separation, so they differ by
    an encoder delay and a gain. Solving for both leaves a residual that is
    mostly voice -- more than good enough to read a melody off.
    """
    mix, _ = librosa.load(str(mix_path), sr=SR, mono=True)
    ins, _ = librosa.load(str(inst_path), sr=SR, mono=True)
    n = min(len(mix), len(ins))
    mix, ins = mix[:n].astype(np.float64), ins[:n].astype(np.float64)
    probe = slice(n // 3, n // 3 + SR * 10)
    a = mix[probe]
    # Coarse lag from a cross-correlation, then a gain solved at that lag.
    span = 2000
    b = ins[probe.start - span : probe.stop + span]
    size = 1 << int(np.ceil(np.log2(len(b) + len(a))))
    corr = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
    lag = int(np.argmax(np.abs(corr[: 2 * span + 1]))) - span
    b = ins[probe.start + lag : probe.start + lag + len(a)]
    scale = float(np.dot(a, b) / max(np.dot(b, b), 1e-9))
    shifted = np.roll(ins, -lag) * scale
    return mix - shifted, SR


def track(vocal: np.ndarray, sr: int, frame_period: float = 10.0):
    f0, t = pw.harvest(vocal, sr, f0_floor=70.0, f0_ceil=900.0, frame_period=frame_period)
    f0 = pw.stonemask(vocal, f0, t, sr)
    return f0, t


def _fold(cands: np.ndarray) -> float:
    """Median of candidate references, with octave outliers folded in."""
    lg = np.log2(cands)
    m = float(np.median(lg))
    for _ in range(3):
        lg = lg - np.round(lg - m)
        m = float(np.median(lg))
    return float(2**m)


def estimate(h: Hollow, mix: Path, inst: Path, min_slots: int = 3) -> dict[int, float]:
    """Per line: where its first pitched slot actually sits, in Hz."""
    vocal, sr = vocal_residual(mix, inst)
    f0, t = track(vocal, sr)
    step = float(t[1] - t[0]) if len(t) > 1 else 0.01
    out: dict[int, float] = {}
    for line in h.lines:
        cands = []
        for s in line.slots:
            if s.pitch is None:
                continue
            i0 = int(s.t / step)
            i1 = int((s.t + min(s.sustain, 0.5)) / step)
            seg = f0[i0 : max(i1, i0 + 2)]
            seg = seg[seg > 0]
            if seg.size < 3:
                continue
            cands.append(float(np.median(seg)) * 2 ** (-s.pitch / 12))
        if len(cands) >= min_slots:
            out[line.id] = round(_fold(np.array(cands)), 2)
    return out


def load_or_measure(h: Hollow, song_dir: Path, cache: Path) -> tuple[dict[int, float], str]:
    """ref_hz per line, and where it came from."""
    have = {l.id: l.ref_hz for l in h.lines if l.ref_hz}
    if len(have) >= len(h.lines) * 0.8:
        return have, "hollow"
    if cache.exists():
        return {int(k): v for k, v in json.loads(cache.read_text()).items()}, "measured (cached)"
    got = estimate(h, song_dir / "mix.mp3", song_dir / "instrumental.mp3")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({str(k): v for k, v in got.items()}, indent=1))
    return got, "measured"
