"""Audio work that happens on this machine and never leaves it.

Source separation (so the player has the instrumental of the recording that was
actually loaded), a voicing envelope (so we can measure how long a syllable is
really held rather than how long it is until the next one), and a pitch track
(so the representation can say how the melody moves).
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 16000  # everything we measure is done at 16 kHz mono


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load(path: str | Path, sr: int = SR) -> np.ndarray:
    import librosa

    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y


def duration(path: str | Path) -> float:
    import librosa

    return float(librosa.get_duration(path=str(path)))


def separate(mix: str | Path, out_dir: str | Path, log=print) -> tuple[Path, Path]:
    """Split a recording into its vocal and its backing track, with Demucs.

    Returns (vocals, instrumental). The instrumental is the backing track of
    this exact recording -- not a synthesised stand-in and not another take.
    """
    mix, out_dir = Path(mix), Path(out_dir)
    vocals = out_dir / f"{mix.stem}.vocals.wav"
    instrumental = out_dir / f"{mix.stem}.instrumental.wav"
    if vocals.exists() and instrumental.exists():
        return vocals, instrumental

    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"separating {mix.name} with Demucs — this takes a few minutes on CPU")
    work = out_dir / "_demucs"
    subprocess.run(
        [sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs",
         "-o", str(work), str(mix)],
        check=True,
    )
    produced = sorted(work.glob(f"htdemucs/{mix.stem}/*.wav"))
    got = {p.stem: p for p in produced}
    if "vocals" not in got or "no_vocals" not in got:
        raise RuntimeError(f"Demucs produced {list(got)} for {mix}")
    got["vocals"].replace(vocals)
    got["no_vocals"].replace(instrumental)
    return vocals, instrumental


@dataclass
class Voicing:
    """Where the vocal is actually sounding, and at what pitch."""

    hop: float  # seconds per frame
    rms: np.ndarray
    f0: np.ndarray  # hertz, NaN where unvoiced
    floor: float  # rms below this is silence
    flux: np.ndarray = None  # where the vocal is getting louder — note attacks

    def voiced(self, t: float) -> bool:
        i = int(t / self.hop)
        return 0 <= i < len(self.rms) and self.rms[i] > self.floor

    def offset_after(self, t: float, limit: float) -> float:
        """When the voice stops after `t`, searched no further than `limit`.

        This is how a held note is measured. It is also what stops the last
        word before an instrumental break from appearing to last four seconds.
        """
        i, j = int(t / self.hop), min(int(limit / self.hop), len(self.rms))
        quiet = 0
        for k in range(i, j):
            if self.rms[k] <= self.floor:
                quiet += 1
                if quiet >= 3:  # ~3 frames of silence ends the note
                    return (k - quiet + 1) * self.hop
            else:
                quiet = 0
        return limit

    def median_f0(self, t0: float, t1: float) -> float | None:
        i, j = int(t0 / self.hop), max(int(t1 / self.hop), int(t0 / self.hop) + 1)
        seg = self.f0[i:j]
        seg = seg[~np.isnan(seg)]
        return float(np.median(seg)) if len(seg) else None

    def activity(self) -> np.ndarray:
        """Per-frame 0/1 vocal activity."""
        return (self.rms > self.floor).astype(np.float32)

    def coverage(self, t0: float, t1: float) -> float:
        """Fraction of a span in which the voice is sounding.

        A line that claims four seconds of singing over silence is a line the
        aligner has put in the wrong place.
        """
        i, j = int(t0 / self.hop), min(int(t1 / self.hop), len(self.rms))
        return float(self.activity()[i:j].mean()) if j > i else 0.0


def analyse(vocals: str | Path, hop_s: float = 0.01) -> Voicing:
    """Measure the vocal stem: energy envelope and pitch track."""
    import librosa

    y = load(vocals)
    hop = max(1, int(round(hop_s * SR)))
    rms = librosa.feature.rms(y=y, frame_length=hop * 4, hop_length=hop)[0]
    # Silence floor from the quiet end of the distribution, not an absolute
    # threshold, so it survives quiet mixes and loud ones alike.
    floor = max(float(np.percentile(rms, 25)) * 2.0, float(rms.max()) * 0.02)

    f0 = librosa.yin(y, fmin=65, fmax=1000, sr=SR, frame_length=hop * 8, hop_length=hop)
    f0 = np.where(rms[: len(f0)] > floor, f0[: len(rms)], np.nan)

    db = librosa.amplitude_to_db(rms, ref=np.max(rms))
    flux = np.maximum(0.0, np.diff(np.maximum(db, -60.0), prepend=db[0]))

    n = min(len(rms), len(f0), len(flux))
    return Voicing(hop=hop / SR, rms=rms[:n], f0=f0[:n], floor=floor, flux=flux[:n])


def semitones(hz: float, ref: float) -> int:
    return int(round(12 * np.log2(max(hz, 1e-6) / max(ref, 1e-6))))


def to_mp3(src: str | Path, dst: str | Path) -> Path:
    """Small mp3 for the browser to stream."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-codec:a", "libmp3lame", "-b:a", "128k", str(dst)],
        check=True,
    )
    return dst
