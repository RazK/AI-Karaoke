#!/usr/bin/env python3
"""Build a single HTML file that plays one song with nobody else's help.

    python tools/standalone.py "Feel (Stripped)" -o out/hollow-karaoke.html

Everything goes inside the file: the lines, every take of them, and the backing
track as a data URI. There is no server behind it, so it can be published
somewhere and opened in a browser -- which is the only way anyone else gets to
see this without installing Demucs and a speech model first.

It plays; it does not ingest. Separating a recording and transcribing its vocal
are minutes of local CPU and several gigabytes of model weights, and neither
happens in a browser tab.

Only publish a song whose licence allows it. Two of the seeded songs are CC
BY-ND, and a karaoke rendition is a derivative -- see LICENSING.md. This script
refuses those rather than leaving it to memory.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.library import Library
from hollow.timing import word_times

TEMPLATE = Path("app/standalone/page.tpl")
BITRATE = "64k"  # mono; a backing track does not need more, and the file is the page


def build(title: str, out: Path, licence_note: str) -> Path:
    lib = Library()
    song = next((s for s in lib.songs() if s.title == title), None)
    if song is None:
        raise SystemExit(f"not in the library: {title!r}")
    if "ND" in licence_note:
        raise SystemExit(
            f"{title} is licensed {licence_note}: no derivatives. A karaoke "
            "rendition is a derivative — play it locally, do not publish it.")

    h, originals = lib.hollow(song.ref), lib.originals(song.ref)
    takes = sorted(lib.dressings(song.ref), key=lambda d: d["licence"])
    if not takes:
        raise SystemExit(f"{title} has no rewrites yet — make one in the app first")

    small = Path(".work") / f"{song.ref}.{BITRATE}.mp3"
    small.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(lib.dir(song.ref) / "instrumental.mp3"),
                    "-ac", "1", "-b:a", BITRATE, str(small)], check=True)

    ow = word_times(h, originals)
    bundle = {
        "title": song.title, "artist": song.artist, "licence": licence_note,
        "duration": song.duration,
        "lines": [{"i": l.id, "s": round(l.start, 3), "e": round(l.end, 3),
                   "u": l.uncertain,
                   "o": originals[l.id] if l.id < len(originals) else "",
                   "ow": ow[l.id] if l.id < len(ow) else []}
                  for l in h.lines],
        "takes": [{"name": d["name"], "licence": d["licence"], "corpus": d["corpus"],
                   "lines": d["lines"], "words": d["words"],
                   "score": d["card"]["singable"], "bends": len(d["bends"]),
                   "fromCorpus": d["card"]["corpus_fidelity"]}
                  for d in takes],
        "audio": "data:audio/mpeg;base64,"
                 + base64.b64encode(small.read_bytes()).decode(),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        TEMPLATE.read_text(encoding="utf-8").replace(
            "__BUNDLE__", json.dumps(bundle, separators=(",", ":"))),
        encoding="utf-8")
    mb = out.stat().st_size / 1e6
    print(f"{song.title} — {song.artist} ({licence_note})")
    print(f"  {len(h.lines)} lines, {len(takes)} takes, {mb:.2f} MB -> {out}")
    if mb > 15:
        print("  warning: over 15 MB. Most hosts cap a page at 16.")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("title", help="a song title as it appears in the library")
    ap.add_argument("-o", "--out", default="out/standalone.html")
    ap.add_argument("--licence", default="CC BY 3.0",
                    help="the song's licence, shown on the page and checked here")
    a = ap.parse_args()
    build(a.title, Path(a.out), a.licence)
