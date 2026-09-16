#!/usr/bin/env python3
"""Write a rewritten song out as text you can read in any editor.

    python tools/text.py "Never Gonna Give You Up" yelp-reviews-1star --dial 0
    python tools/text.py --all                 # every song against every corpus

Three files per combination, in out/text/:

  <song>--<corpus>--<dial>.txt             the original and the rewrite, side by
                                           side, section by section
  <...>.original.txt / <...>.rewritten.txt the same two columns as two files of
                                           equal length, for a real editor split

Nothing here plays anything. The point is to decide whether the words are any
good before a minute goes into the player.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.dress import QUOTE_END, anthropic_writer, dress
from hollow.exam import score
from hollow.library import Library

OUT = Path("out/text")
DATA = Path("data/datasets")
WIDTH = 44


def dial_name(licence: float) -> str:
    if licence <= QUOTE_END:
        return "quote — only phrases the text already contains"
    if licence < 0.75:
        return "blend — the text's own phrases where they fit, reworded where they do not"
    return "rephrase — the text's ideas, reworded to fit"


def clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def render(song, h, originals, d, s) -> str:
    """The two columns, with the sections and the repeats marked."""
    lifted = sum(d.from_corpus)
    bent = {b.line for b in d.bends}
    out = [
        f"{song.title} — {song.artist}",
        f"{d.corpus} · dial {d.licence:.2f} · {dial_name(d.licence)}",
        f"{s.score:.2f}/10 singable · {lifted}/{len(h.lines)} lines are the "
        f"corpus's own words · {len(d.bends)} bent",
        "",
        "  =  this line repeats an earlier one — the chorus, sung the same way",
        "  !  the tune had to bend here",
        "  ?  the aligner was unsure of this line; it is left out of the score",
        "",
    ]
    for si, ids in enumerate(h.sections):
        source = h.section_echo[si] if si < len(h.section_echo) else None
        when = clock(h.lines[ids[0]].start)
        head = f"SECTION {si + 1}  ({when})"
        if source is not None:
            head += f"   — the same words as section {source + 1}"
        out += [head, "-" * (WIDTH * 2 + 6)]
        for lid in ids:
            was = (originals[lid] if lid < len(originals) else "")[:WIDTH]
            now = d.lines[lid]
            mark = "=" if d.echo_of[lid] is not None else ("!" if lid in bent else
                   ("?" if h.lines[lid].uncertain else " "))
            out.append(f" {mark} {was:<{WIDTH}}  |  {now}")
        out.append("")

    if d.bends:
        out += ["WHERE THE TUNE HAD TO BEND", ""]
        out += [f"  {b}" for b in d.bends]
    else:
        out += ["No line had to bend: every one has exactly the syllables the "
                "tune asks for."]
    return "\n".join(out) + "\n"


def build(song, h, originals, corpus_name: str, corpus_text: str,
          licence: float, writer) -> None:
    d = dress(h, corpus_text, licence, corpus_name=corpus_name,
              writer=writer, log=lambda *a: None)
    s = score(h, d.lines)
    stem = f"{slug(song.title)}--{slug(corpus_name)}--{int(round(licence * 100)):03d}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}.txt").write_text(render(song, h, originals, d, s), encoding="utf-8")
    (OUT / f"{stem}.original.txt").write_text(
        "\n".join(originals[l.id] if l.id < len(originals) else "" for l in h.lines)
        + "\n", encoding="utf-8")
    (OUT / f"{stem}.rewritten.txt").write_text(
        "\n".join(d.lines) + "\n", encoding="utf-8")
    inside = sum(1 for si, ids in enumerate(h.sections)
                 for lid in ids if d.echo_of[lid] is not None)
    print(f"  {song.title[:26]:28} {corpus_name:20} {licence:.2f}  "
          f"{s.score:5.2f}/10  own words {sum(d.from_corpus):3d}/{len(h.lines)}  "
          f"bends {len(d.bends):2d}  repeated lines {inside:2d}  -> {stem}.txt")


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:40]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("song", nargs="?", help="a song title as it appears in the library")
    ap.add_argument("corpus", nargs="?", help="a corpus id from data/datasets")
    ap.add_argument("--dial", type=float, default=0.0)
    ap.add_argument("--all", action="store_true",
                    help="every library song against every bundled corpus")
    ap.add_argument("--dials", default="",
                    help="comma-separated dial settings, e.g. 0,0.5,1")
    args = ap.parse_args()

    for name in (".env.local", ".env"):
        f = Path(name)
        if f.exists():
            for line in f.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

    lib = Library()
    songs = lib.songs()
    if not songs:
        print("no songs in the library")
        return 1

    dials = [float(x) for x in args.dials.split(",")] if args.dials else [args.dial]
    if any(d > QUOTE_END for d in dials) and not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"a dial above {QUOTE_END} needs ANTHROPIC_API_KEY in .env.local; "
              "below it, nothing is charged and no model is called", file=sys.stderr)
        return 1
    writer = anthropic_writer() if any(d > QUOTE_END for d in dials) else None

    if args.all:
        pairs = [(s, c.stem) for s in songs for c in sorted(DATA.glob("*.txt"))]
    else:
        if not args.song or not args.corpus:
            print("give a song and a corpus, or --all", file=sys.stderr)
            return 1
        song = next((s for s in songs if s.title == args.song), None)
        if song is None:
            print(f"not in the library: {args.song!r}\n  have: "
                  + ", ".join(repr(s.title) for s in songs), file=sys.stderr)
            return 1
        pairs = [(song, args.corpus)]

    for song, corpus in pairs:
        path = DATA / f"{corpus}.txt"
        if not path.exists():
            print(f"no corpus called {corpus}", file=sys.stderr)
            return 1
        h, originals = lib.hollow(song.ref), lib.originals(song.ref)
        for licence in dials:
            build(song, h, originals, corpus, path.read_text(encoding="utf-8"),
                  licence, writer)
    print(f"\nwrote {OUT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
