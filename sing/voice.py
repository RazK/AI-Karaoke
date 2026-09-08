"""A local text-to-speech voice, asked for one syllable at a time.

Piper (VITS, ONNX, CPU) with the en_US-lessac-medium voice. Nothing leaves the
machine: the model is a local file and every syllable is synthesised here.

The voice speaks; it does not sing. All this module has to give the rest of the
renderer is a clean, correctly pronounced syllable at its natural speaking
length. Pitch and duration are taken away and rebuilt in `sing.world`.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from .phones import Unit

DEFAULT_MODEL = Path(".work/piper/en_US-lessac-medium.onnx")


class Voice:
    def __init__(
        self,
        model: str | Path | None = None,
        length_scale: float = 1.0,
        takes: str | Path | None = None,
    ):
        from piper import PiperVoice, SynthesisConfig

        path = Path(model or os.environ.get("PIPER_MODEL", DEFAULT_MODEL))
        self.voice = PiperVoice.load(str(path))
        self.sr = self.voice.config.sample_rate
        # The same syllable must come out the same every time it is sung, or a
        # repeated word wobbles for no musical reason. Low noise gets most of
        # the way there; the rest is the decoder sampling its own latent, which
        # nothing in the ONNX graph lets us seed -- so the takes are kept on
        # disk instead, and a re-render is the same performance rather than a
        # new one.
        self.cfg = SynthesisConfig(
            length_scale=length_scale, noise_scale=0.333, noise_w_scale=0.333
        )
        self.takes = Path(takes or path.with_suffix(".takes.npz"))
        self._cache: dict[tuple[str, ...], tuple[np.ndarray, int, int]] = {}
        self._dirty = False
        if self.takes.exists():
            with np.load(self.takes, allow_pickle=False) as z:
                for k in z.files:
                    if k.endswith("|n"):
                        continue
                    ns, ne = (int(x) for x in z[k + "|n"])
                    self._cache[tuple(k.split("\x1f"))] = (z[k].astype(np.float64), ns, ne)

    def save(self) -> None:
        """Keep every syllable this render used, so the next one matches it."""
        if not self._dirty:
            return
        out = {}
        for k, (a, ns, ne) in self._cache.items():
            key = "\x1f".join(k)
            out[key] = a.astype(np.float32)
            out[key + "|n"] = np.array([ns, ne], dtype=np.int64)
        self.takes.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(self.takes, **out)
        self._dirty = False

    def say(self, u: Unit) -> tuple[np.ndarray, int, int]:
        """Audio for one syllable, plus the sample range holding its vowel.

        The vowel range is estimated from the audio (the ONNX voice exposes no
        alignments), by finding the loudest voiced stretch. Consonants that can
        be sung -- l, m, n, r -- may be swept up into it, which is harmless:
        they are the ones a singer sustains anyway.
        """
        key = u.phonemes
        if key not in self._cache:
            ids = self.voice.phonemes_to_ids(list(u.phonemes))
            # float32 now, not at save time, so the take that goes to disk is
            # bit-for-bit the take this render used.
            audio = np.asarray(
                self.voice.phoneme_ids_to_audio(ids, self.cfg), dtype=np.float32
            ).astype(np.float64)
            audio = _trim(audio)
            if audio.size < 256:  # the voice refused; a hummed fallback
                audio = _hum(self.sr)
            self._cache[key] = (audio, *_nucleus(audio, self.sr))
            self._dirty = True
        return self._cache[key]


def _trim(a: np.ndarray, floor_db: float = -42.0) -> np.ndarray:
    """Drop the silence piper pads around a short utterance."""
    if a.size == 0:
        return a
    win = 128
    n = a.size // win * win
    if n == 0:
        return a
    frames = np.abs(a[:n]).reshape(-1, win).max(axis=1)
    peak = frames.max()
    if peak <= 0:
        return a
    live = np.flatnonzero(frames > peak * 10 ** (floor_db / 20))
    if live.size == 0:
        return a
    lo = max(0, (live[0] - 1) * win)
    hi = min(a.size, (live[-1] + 2) * win)
    return a[lo:hi]


def _nucleus(a: np.ndarray, sr: int) -> tuple[int, int]:
    """Sample range of the syllable's sustainable core."""
    win = max(1, sr // 200)  # 5 ms
    n = a.size // win
    if n < 3:
        return 0, a.size
    e = np.sqrt((a[: n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    # Zero-crossing rate separates a loud fricative (s, sh, f) from a vowel.
    frames = a[: n * win].reshape(n, win)
    zcr = (np.diff(np.sign(frames), axis=1) != 0).mean(axis=1)
    score = e * (zcr < 0.25)
    if not score.any():
        return 0, a.size
    peak = int(np.argmax(score))
    thr = score[peak] * 0.35
    lo = peak
    while lo > 0 and score[lo - 1] >= thr:
        lo -= 1
    hi = peak
    while hi + 1 < n and score[hi + 1] >= thr:
        hi += 1
    return lo * win, min(a.size, (hi + 1) * win)


def _hum(sr: int) -> np.ndarray:
    """Last resort: a short buzz, so a slot is never silently dropped."""
    t = np.arange(int(0.25 * sr)) / sr
    return 0.2 * np.sin(2 * np.pi * 160 * t) * np.hanning(t.size)
