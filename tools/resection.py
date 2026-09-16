#!/usr/bin/env python3
"""Work out the sections and repeats of songs that were ingested before it did.

    python tools/resection.py

A song extracted before the format knew about choruses has no sections and no
repeat labels, and falls back to its breath groups, which are no use for writing
a song a part at a time. The original words are still on this machine next to
the representation, so the answer can be recomputed without fetching, separating
or transcribing anything again.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.format import echo_labels, sections_from
from hollow.library import Library


def main() -> int:
    lib = Library()
    songs = lib.songs()
    if not songs:
        print("no songs in the library")
        return 1

    for song in songs:
        h = lib.hollow(song.ref)
        texts = lib.originals(song.ref)
        if len(texts) != len(h.lines):
            print(f"  {song.title[:30]:32} SKIPPED — {len(texts)} originals "
                  f"for {len(h.lines)} lines")
            continue

        shapes = [(len(l.slots), tuple(s.stress for s in l.slots)) for l in h.lines]
        echoes = echo_labels(texts, shapes)
        for line, e in zip(h.lines, echoes):
            line.echo = e
        h.sections, h.section_echo = sections_from(echoes, h.groups, len(h.lines))
        h.save(lib.dir(song.ref) / "hollow.json")

        repeats = sum(1 for e in h.section_echo if e is not None)
        sizes = [len(s) for s in h.sections]
        print(f"  {song.title[:30]:32} {len(h.sections):2d} sections "
              f"({repeats} repeated), sizes {sizes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
