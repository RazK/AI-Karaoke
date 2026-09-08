"""Render a song from its HOLLOW twice: its own words, and someone else's.

    .venv/bin/python -m sing.cli --song <ref> --corpus ikea-manuals

Everything runs locally. No lyric ever leaves the machine.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from hollow import exam
from hollow.dress import dress
from hollow.library import Library

from . import mixdown, refhz
from .render import sing
from .voice import Voice

OUT = Path("out/sing")
CACHE = OUT / ".cache"


def pick_song(lib: Library, want: str | None):
    songs = lib.songs()
    if not songs:
        raise SystemExit("the library is empty")
    if want:
        s = lib.get(want)
        if not s:
            raise SystemExit(f"no song {want}; have {[x.ref for x in songs]}")
        return s
    # the song the aligner is surest about, biggest first
    return max(songs, key=lambda s: (-s.uncertain_lines, s.n_lines))


def fill_gaps(refs: dict[int, float], n_lines: int, fold: bool) -> dict[int, float]:
    """Every line needs a reference; the ones without borrow from neighbours.

    `fold` pulls every line into a single octave. It is off by default: with
    the extractor's own ref_hz, folding makes the rendered melody *further*
    from the recording (9 lines an octave out instead of 3), because this song
    really does move between octaves. It is here for representations whose
    ref_hz comes from an f0 tracker that slips.
    """
    if not refs:
        return {}
    med = float(np.median(list(refs.values())))
    out = {}
    for i in range(n_lines):
        if i in refs:
            hz = refs[i]
            if fold:
                hz = hz * 2 ** -round(np.log2(hz / med))
        else:
            near = sorted(refs, key=lambda j: abs(j - i))[:3]
            hz = float(np.median([refs[j] for j in near]))
            if fold:
                hz = hz * 2 ** -round(np.log2(hz / med))
        out[i] = round(hz, 2)
    return out


def render_one(h, lines, refs, voice, song_dir: Path, out_mp3: Path, wav: Path | None):
    t0 = time.time()
    vocal, plans = sing(h, lines, refs, voice)
    if wav:
        sf.write(str(wav), vocal / max(1e-9, np.abs(vocal).max()) * 0.9, voice.sr)
    mixdown.mix(vocal, voice.sr, song_dir / "instrumental.mp3", out_mp3)
    return plans, time.time() - t0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--song", default=None)
    p.add_argument("--corpus", default="ikea-manuals")
    p.add_argument("--licence", type=float, default=0.0)
    p.add_argument("--fold-octaves", action="store_true",
                   help="pull every line into one octave; only helps when the "
                        "f0 tracker behind ref_hz is slipping octaves")
    p.add_argument("--keep-wav", action="store_true", help="also write the bare vocal")
    args = p.parse_args()

    lib = Library()
    song = pick_song(lib, args.song)
    h = lib.hollow(song.ref)
    d = lib.dir(song.ref)
    print(f"song {song.ref}  {song.title} — {song.artist}: "
          f"{len(h.lines)} lines, {h.n_slots} slots, {h.duration:.0f}s")

    measured, source = refhz.load_or_measure(h, d, CACHE / f"refhz-{song.ref}.json")
    refs = fill_gaps(measured, len(h.lines), fold=args.fold_octaves)
    print(f"ref_hz: {source}, {len(measured)}/{len(h.lines)} lines read directly")

    originals = lib.originals(song.ref)
    corpus = Path("data/datasets") / f"{args.corpus}.txt"
    dressing = dress(h, corpus.read_text(encoding="utf-8"), args.licence,
                     corpus_name=args.corpus)

    s_orig = exam.score(h, originals)
    s_dress = exam.score(h, dressing.lines)
    print(f"exam, originals: {s_orig}")
    print(f"exam, dressed  : {s_dress}")

    voice = Voice()
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "song": {"ref": song.ref, "title": song.title, "artist": song.artist,
                 "lines": len(h.lines), "slots": h.n_slots, "duration": h.duration},
        "voice": "piper en_US-lessac-medium (VITS, ONNX, CPU) + WORLD resynthesis",
        "ref_hz": {"source": source, "measured_lines": len(measured),
                   "octave_folded": args.fold_octaves,
                   "median": round(float(np.median(list(refs.values()))), 2) if refs else None},
        "corpus": args.corpus, "licence": args.licence,
        "exam": {"originals": str(s_orig), "dressed": str(s_dress),
                 "originals_score": round(s_orig.score, 2),
                 "dressed_score": round(s_dress.score, 2)},
        "bends": [b.__dict__ for b in dressing.bends],
        "lines": [{"id": i, "original_slots": len(l.slots), "dressed": t}
                  for i, (l, t) in enumerate(zip(h.lines, dressing.lines))],
    }

    for name, lines in (("original", originals), ("dressed", dressing.lines)):
        wav = OUT / f"{name}-vocal.wav" if args.keep_wav else None
        plans, took = render_one(h, lines, refs, voice, d, OUT / f"{name}.mp3", wav)
        notes = sum(len(p.notes) for p in plans)
        off = [(p.line, p.slots, p.written) for p in plans if p.slots != p.written]
        print(f"{name}.mp3: {notes} notes, {len(off)} lines off-count, {took:.0f}s")
        report[name] = {"notes": notes, "seconds_to_render": round(took, 1),
                        "lines_off_count": off}
        voice.save()

    (OUT / "render.json").write_text(json.dumps(report, indent=1))
    print("wrote", OUT / "original.mp3", OUT / "dressed.mp3")


if __name__ == "__main__":
    main()
