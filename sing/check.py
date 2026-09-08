"""Does it actually sing? Two measurements, both local.

Intelligibility: run a speech recogniser over the bare vocal and see how much
of the line it gets back. It is a harsh judge of a synthetic singer -- it was
trained on speech -- so treat it as a floor, not a verdict.

Pitch: read the f0 back off the rendered vocal and compare it, note by note,
with the frequency the representation asked for.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf

from hollow.format import Hollow

from . import melody


def words(s: str) -> list[str]:
    return re.findall(r"[a-z']+", s.lower())


def wer(ref: list[str], hyp: list[str]) -> float:
    d = np.zeros((len(ref) + 1, len(hyp) + 1), int)
    d[:, 0] = np.arange(len(ref) + 1)
    d[0, :] = np.arange(len(hyp) + 1)
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1,
                          d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    return d[-1, -1] / max(1, len(ref))


def transcribe(wav: Path, model: str = "base.en") -> str:
    from faster_whisper import WhisperModel

    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), beam_size=5)
    return " ".join(s.text.strip() for s in segs)


def pitch_error(wav: Path, h: Hollow, refs: dict[int, float]) -> dict:
    """Cents between what was asked for and what came out, per slot."""
    a, sr = sf.read(str(wav))
    a = np.asarray(a, dtype=np.float64)
    f0, t = pw.harvest(a, sr, f0_floor=70.0, f0_ceil=900.0, frame_period=10.0)
    f0 = pw.stonemask(a, f0, t, sr)
    step = float(t[1] - t[0]) if len(t) > 1 else 0.01
    errs, missing = [], 0
    for line in h.lines:
        ref = refs.get(line.id)
        if not ref:
            continue
        hz = melody.line_hz(line, ref)
        for slot, want in zip(line.slots, hz):
            i0 = int((slot.t + 0.25 * slot.sustain) / step)
            i1 = int((slot.t + 0.85 * slot.sustain) / step)
            seg = f0[i0 : max(i1, i0 + 2)]
            seg = seg[seg > 0]
            if seg.size < 2:
                missing += 1
                continue
            got = float(np.median(seg))
            errs.append(1200 * np.log2(got / want))
    e = np.array(errs)
    return {
        "slots_measured": len(e), "slots_unvoiced": missing,
        "median_abs_cents": round(float(np.median(np.abs(e))), 1) if len(e) else None,
        "within_50_cents": round(float((np.abs(e) < 50).mean()), 3) if len(e) else None,
        "within_100_cents": round(float((np.abs(e) < 100).mean()), 3) if len(e) else None,
    }


def tune_error(wav: Path, h: Hollow, refs: dict[int, float], song_dir: Path) -> dict:
    """How close the rendered melody lands to the melody actually sung.

    Slot by slot, on the octave: the original recording's own vocal against
    the rendered one. This is the number that says whether it is the same tune.
    """
    from . import refhz as R

    voc, sr = R.vocal_residual(song_dir / "mix.mp3", song_dir / "instrumental.mp3")
    f0o, t = R.track(voc, sr)
    a, sr2 = sf.read(str(wav))
    f0s, _ = R.track(np.asarray(a, dtype=np.float64), sr2)
    step = float(t[1] - t[0]) if len(t) > 1 else 0.01

    def med(f0, t0, t1):
        seg = f0[int(t0 / step) : max(int(t1 / step), int(t0 / step) + 2)]
        seg = seg[seg > 0]
        return float(np.median(seg)) if seg.size >= 3 else None

    errs = []
    for line in h.lines:
        if line.id not in refs:
            continue
        for slot in line.slots:
            t1 = slot.t + min(slot.sustain, 0.5)
            o, s = med(f0o, slot.t, t1), med(f0s, slot.t, t1)
            if o and s:
                d = np.log2(s / o)
                errs.append(abs(d - round(d)) * 1200)
    e = np.array(errs)
    return {
        "slots_compared": len(e),
        "median_cents_from_original": round(float(np.median(e)), 1) if len(e) else None,
        "within_semitone": round(float((e < 100).mean()), 3) if len(e) else None,
        "within_quartertone": round(float((e < 50).mean()), 3) if len(e) else None,
    }


def main() -> None:
    import argparse

    from hollow.library import Library

    from .cli import CACHE, OUT, fill_gaps

    p = argparse.ArgumentParser()
    p.add_argument("--song", required=True)
    p.add_argument("--model", default="base.en")
    args = p.parse_args()

    lib = Library()
    h = lib.hollow(args.song)
    have = {l.id: l.ref_hz for l in h.lines if l.ref_hz}
    measured = have or {int(k): v for k, v in
                        json.loads((CACHE / f"refhz-{args.song}.json").read_text()).items()}
    refs = fill_gaps(dict(measured), len(h.lines), False)
    said = {"original": lib.originals(args.song),
            "dressed": [l["dressed"] for l in json.loads((OUT / "render.json").read_text())["lines"]]}

    out = {}
    for name, lines in said.items():
        row = {}
        row["pitch_vs_target"] = pitch_error(OUT / f"{name}-vocal.wav", h, refs)
        row["tune_vs_original_recording"] = tune_error(
            OUT / f"{name}-vocal.wav", h, refs, lib.dir(args.song))
        ref_words = words(" ".join(lines))
        for what, path in (("vocal_only", OUT / f"{name}-vocal.wav"),
                           ("full_mix", OUT / f"{name}.mp3")):
            heard = transcribe(path, args.model)
            row[f"wer_{what}"] = round(wer(ref_words, words(heard)), 3)
            row[f"heard_{what}"] = heard
        out[name] = row
        print(name, {k: v for k, v in row.items() if not k.startswith("heard")})
    (OUT / "check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
