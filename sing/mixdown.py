"""Put the voice on the record.

A dry mono voice pasted onto a produced backing track sounds like a voice
pasted onto a backing track, so there is a little reverb here, a high-pass to
get it out of the bass, and a level set against the instrumental so the words
can be heard. None of this is in HOLLOW; it is production, not representation.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import librosa
import numpy as np
from scipy import signal

SR = 44100


def _reverb_ir(sr: int, decay: float = 1.1, predelay: float = 0.02) -> np.ndarray:
    n = int(decay * sr)
    rng = np.random.default_rng(7)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6.0, n))
    b, a = signal.butter(2, 6000 / (sr / 2), "low")
    ir = signal.lfilter(b, a, ir)
    ir[: int(0.005 * sr)] = 0
    return np.concatenate([np.zeros(int(predelay * sr)), ir / np.abs(ir).max()])


def polish(vocal: np.ndarray, sr_in: int, sr: int = SR, wet: float = 0.16) -> np.ndarray:
    v = librosa.resample(vocal, orig_sr=sr_in, target_sr=sr) if sr_in != sr else vocal.copy()
    b, a = signal.butter(2, 110 / (sr / 2), "high")
    v = signal.lfilter(b, a, v)
    # a gentle presence lift, so consonants cut through a full band
    b2, a2 = signal.butter(2, [2200 / (sr / 2), 6500 / (sr / 2)], "band")
    v = v + 0.35 * signal.lfilter(b2, a2, v)
    rev = signal.fftconvolve(v, _reverb_ir(sr))[: len(v)]
    rev *= np.sqrt((v**2).mean()) / (np.sqrt((rev**2).mean()) + 1e-9)
    return (1 - wet) * v + wet * rev


def _limit(x: np.ndarray, ceiling: float = 0.97) -> np.ndarray:
    return np.tanh(x / ceiling) * ceiling


def mix(
    vocal: np.ndarray,
    sr_in: int,
    instrumental: Path,
    out_mp3: Path,
    *,
    vocal_over_band_db: float = 3.0,
) -> Path:
    """Mix the rendered voice over the song's own instrumental and encode."""
    band, _ = librosa.load(str(instrumental), sr=SR, mono=False)
    if band.ndim == 1:
        band = np.stack([band, band])
    v = polish(vocal, sr_in)
    n = max(band.shape[1], len(v))
    band = np.pad(band, ((0, 0), (0, n - band.shape[1])))
    v = np.pad(v, (0, n - len(v)))

    live = np.abs(v) > 0.02 * np.abs(v).max()
    if live.sum() < SR:
        live = np.ones(n, bool)
    v_rms = float(np.sqrt((v[live] ** 2).mean()) + 1e-9)
    b_rms = float(np.sqrt((band[:, live] ** 2).mean()) + 1e-9)
    gain = (b_rms / v_rms) * 10 ** (vocal_over_band_db / 20)
    v = v * gain

    stereo = band * 0.80 + np.stack([v, v]) * 0.85
    peak = float(np.abs(stereo).max())
    if peak > 0:
        stereo = stereo / peak * 0.95
    stereo = _limit(stereo)

    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    raw = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR),
         "-ac", "2", "-i", "pipe:0", "-codec:a", "libmp3lame", "-b:a", "192k",
         str(out_mp3)],
        input=raw, check=True,
    )
    return out_mp3
