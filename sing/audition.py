"""Cast the singer.

Piper's decoder samples its own latent, so every render is a different take of
the same score -- and the takes are not equally good. Two takes of this song
measured 0.15 and 0.36 word error apart from each other with nothing else
changed. So instead of shipping whichever take came out of the last run, this
records a few, listens to them with a speech recogniser, and keeps the one
whose words come back clearest.

    .venv/bin/python -m sing.audition --song <ref> --trials 4

The winner is left in the voice's takes file, so the next `sing.cli` render is
that take, exactly.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

from hollow.dress import dress
from hollow.library import Library

from . import check, refhz
from .cli import CACHE, OUT, fill_gaps, pick_song
from .render import sing
from .voice import Voice

SCRATCH = Path(".work/audition")


def take_score(voice: Voice, h, said: dict[str, list[str]], refs, model: str) -> float:
    """Mean word error over both lyrics: one number for the take as a whole."""
    errs = []
    for name, lines in said.items():
        vocal, _ = sing(h, lines, refs, voice, log=lambda *_: None)
        wav = SCRATCH / f"{name}.wav"
        sf.write(str(wav), vocal / max(1e-9, np.abs(vocal).max()) * 0.9, voice.sr)
        heard = check.transcribe(wav, model)
        errs.append(check.wer(check.words(" ".join(lines)), check.words(heard)))
    return float(np.mean(errs))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--song", default=None)
    p.add_argument("--corpus", default="ikea-manuals")
    p.add_argument("--licence", type=float, default=0.0)
    p.add_argument("--trials", type=int, default=4)
    p.add_argument("--model", default="base.en")
    args = p.parse_args()

    lib = Library()
    song = pick_song(lib, args.song)
    h = lib.hollow(song.ref)
    measured, _ = refhz.load_or_measure(h, lib.dir(song.ref), CACHE / f"refhz-{song.ref}.json")
    refs = fill_gaps(measured, len(h.lines), fold=False)
    corpus = (Path("data/datasets") / f"{args.corpus}.txt").read_text(encoding="utf-8")
    said = {"original": lib.originals(song.ref),
            "dressed": dress(h, corpus, args.licence, corpus_name=args.corpus,
                             log=lambda *_: None).lines}

    SCRATCH.mkdir(parents=True, exist_ok=True)
    canonical = Voice().takes
    best: tuple[float, Path] | None = None
    for i in range(args.trials):
        canonical.unlink(missing_ok=True)
        voice = Voice()
        score = take_score(voice, h, said, refs, args.model)
        voice.save()
        kept = SCRATCH / f"take-{i}.npz"
        shutil.copyfile(canonical, kept)
        print(f"take {i}: mean word error {score:.3f}")
        if best is None or score < best[0]:
            best = (score, kept)

    assert best is not None
    shutil.copyfile(best[1], canonical)
    print(f"kept the take at {best[0]:.3f}; re-run sing.cli to mix it")
    (OUT / ".cache").mkdir(parents=True, exist_ok=True)
    (OUT / ".cache" / "audition.txt").write_text(
        f"{args.trials} takes auditioned, best mean word error {best[0]:.3f}\n")


if __name__ == "__main__":
    main()
