#!/usr/bin/env python3
"""Song in, karaoke file out.

    python tools/lrc.py <youtube-url | audio-file> <text-file> [options]

Takes a recording -- fetched from a YouTube URL or a file you already have --
and a body of text, and writes a word-level .lrc of the song rewritten out of
that text. Nothing is played and nothing is served; the .lrc is the whole
output, so you can open it in any karaoke player and see whether it lands.

    python tools/lrc.py https://youtu.be/... ikea.txt --licence 0.6
    python tools/lrc.py song.mp3 reviews.txt -o out.lrc

The song's own words never leave this machine. What reaches the language model
is the word-free HOLLOW rendering and the text you supplied.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.dress import anthropic_writer, dress
from hollow.exam import score
from hollow.extract import TimedWord
from hollow.ingest import fetch_youtube, ingest, to_lrc
from hollow.timing import word_times

WORK = Path(".work/lrc")


def load_env() -> None:
    """Read .env.local, so the key lives next to the project and not in it."""
    for name in (".env.local", ".env"):
        f = Path(name)
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def is_url(text: str) -> bool:
    return text.startswith(("http://", "https://", "www."))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("song", help="a YouTube URL, or a path to an audio file")
    ap.add_argument("text", help="a text file to rewrite the song out of")
    ap.add_argument("--licence", type=float, default=0.0,
                    help="0 keeps to the text's own phrases and calls no model; "
                         "1 lets the model rewrite freely (default 0)")
    ap.add_argument("-o", "--out", help="where to write the .lrc")
    ap.add_argument("--title", default="")
    ap.add_argument("--artist", default="")
    args = ap.parse_args()

    load_env()
    corpus = Path(args.text).read_text(encoding="utf-8")
    if not corpus.strip():
        print("that text file is empty", file=sys.stderr)
        return 1

    # Everything that can be checked before the slow part is checked before it.
    # Separating and transcribing a song takes minutes; finding out at the end
    # of them that a key is missing is a waste of somebody's afternoon.
    writer = None
    if args.licence > 0:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("licence above 0 needs ANTHROPIC_API_KEY in .env.local "
                  "(or use --licence 0, which calls no model)", file=sys.stderr)
            return 1
        writer = anthropic_writer()

    # 1. Get the recording.
    if is_url(args.song):
        mix, meta = fetch_youtube(args.song, WORK / "downloads")
        title = args.title or meta["title"]
        artist = args.artist or meta["artist"]
        kind = "youtube"
    else:
        mix = Path(args.song)
        if not mix.exists():
            print(f"no such file: {mix}", file=sys.stderr)
            return 1
        title = args.title or mix.stem
        artist = args.artist
        kind = "upload"
    print(f"song: {title}" + (f" — {artist}" if artist else ""))

    # 2. Recording -> HOLLOW. Separation and transcription both run here.
    h, _originals, _instrumental, _mix = ingest(
        mix, source_kind=kind, work_dir=WORK / mix.stem,
    )

    # 3. Text -> words on the song.
    d = dress(h, corpus, args.licence, corpus_name=Path(args.text).stem, writer=writer)

    # 4. The words, with the times they are sung, as a karaoke file.
    rows = word_times(h, d.lines)
    timed = [TimedWord(w["w"], w["t"], w["t"] + w["d"], i)
             for i, row in enumerate(rows) for w in row]
    meta = {"ti": title, "ar": artist, "by": "AI Karaoke"}
    out = Path(args.out) if args.out else Path(f"{mix.stem}.rewritten.lrc")
    out.write_text(to_lrc(timed, {k: v for k, v in meta.items() if v}),
                   encoding="utf-8")

    # 5. Say how it went.
    s = score(h, d.lines)
    print(f"\nsingability {s.score:.2f}/10   {len(h.lines)} lines, {h.n_slots} slots")
    if d.bends:
        print(f"{len(d.bends)} line(s) where the tune had to bend:")
        for b in d.bends:
            print(f"  {b}")
    else:
        print("no line had to bend — every one has exactly the syllables the tune asks")
    if s.excluded:
        print(f"{len(s.excluded)} line(s) the aligner was unsure of, left out of the score")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
