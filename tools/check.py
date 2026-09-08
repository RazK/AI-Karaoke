#!/usr/bin/env python3
"""Check a writer's answer against the rows it was given, before it is accepted.

    python tools/check.py out/prompts/<combo>/<key>

Reads <key>.prompt.txt and <key>.answer.txt and says, per line, whether the
syllables land and where the stress disagrees. The point is to let whoever is
writing see what is wrong without having to run the whole pipeline.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow import prosody

ROW = re.compile(r"^\s*L(\d+)\s*\[(\w)\]\s*(\d+)\s+([●○_ ]+?)(?:\s{2,}|$)", re.M)
ANSWER = re.compile(r"^\s*L?(\d+)\s*[:.\)]\s*(.+?)\s*$", re.M)


def main(key: str) -> int:
    key = key[: -len(".prompt.txt")] if key.endswith(".prompt.txt") else key
    prompt = Path(key + ".prompt.txt").read_text(encoding="utf-8")
    answer_path = Path(key + ".answer.txt")
    if not answer_path.exists():
        print(f"no answer yet at {answer_path}")
        return 1
    answers = {int(m.group(1)): m.group(2).strip(' "')
               for m in ANSWER.finditer(answer_path.read_text(encoding="utf-8"))}

    wanted = [m for m in ROW.finditer(prompt) if "write this one" in
              prompt[m.start():prompt.find("\n", m.start())]]
    bad = 0
    for m in wanted:
        lid, rhyme, n = int(m.group(1)), m.group(2), int(m.group(3))
        asks = [g.startswith("●") for g in m.group(4).split()]
        text = answers.get(lid)
        if text is None:
            print(f"  L{lid:02d} [{rhyme}] wants {n:2d}  MISSING")
            bad += 1
            continue
        syls = prosody.syllables_for(text, n)
        hits = sum(s.stressed == a for s, a in zip(syls, asks))
        ok = len(syls) == n
        bad += not ok
        flag = "ok " if ok else "OUT"
        print(f"  L{lid:02d} [{rhyme}] wants {n:2d} got {len(syls):2d} {flag} "
              f"stress {hits}/{min(len(syls), n)}  {text}")
    print(f"{len(wanted) - bad}/{len(wanted)} lines land exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
