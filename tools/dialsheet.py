#!/usr/bin/env python3
"""Put one song's dial settings next to each other, in one file.

    python tools/dialsheet.py never-gonna-give-you-up ikea-manuals

Reads what `tools/text.py` already wrote in out/text/ -- nothing is generated
and nothing is charged. The point is to see the dial move: the same line of the
same song, quoted, blended and rephrased, on one row.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("out/text")
W = 34


def read(stem: str, kind: str) -> list[str]:
    path = OUT / f"{stem}.{kind}.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def cut(text: str, width: int = W) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def main() -> int:
    if len(sys.argv) < 3:
        print("give a song slug and a corpus slug, as they appear in out/text/",
              file=sys.stderr)
        return 1
    song, corpus = sys.argv[1], sys.argv[2]
    dials = [("0.00", "quote"), ("0.60", "blend"), ("1.00", "rephrase")]

    cols, have = [], []
    originals: list[str] = []
    for tag, name in dials:
        stem = f"{song}--{corpus}--{tag.replace('.', '')}"
        rewritten = read(stem, "rewritten")
        if not rewritten:
            continue
        originals = originals or read(stem, "original")
        cols.append(rewritten)
        have.append((tag, name))
    if not cols:
        print(f"nothing in {OUT}/ for {song} × {corpus}", file=sys.stderr)
        return 1

    head = f"{'THE SONG':<{W}}  " + "  ".join(
        f"{name + ' ' + tag:<{W}}" for tag, name in have)
    out = [
        f"{song} × {corpus} — the dial, end to end",
        "",
        "Left: the words as sung. Then the same line rewritten out of the text,",
        "at each setting of the one control. Same tune, same timing, every column.",
        "",
        head,
        "-" * len(head.rstrip()),
    ]
    for i in range(max(len(originals), *(len(c) for c in cols))):
        row = [cut(originals[i] if i < len(originals) else "")]
        row += [cut(c[i] if i < len(c) else "") for c in cols]
        out.append("  ".join(f"{x:<{W}}" for x in row).rstrip())

    path = OUT / f"DIAL--{song}--{corpus}.txt"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
