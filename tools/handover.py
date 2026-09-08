#!/usr/bin/env python3
"""Generate the nine songs and write them out as something you can read.

    python tools/handover.py            build every combination that is ready
    python tools/handover.py --pending  list the prompts still waiting on a writer

Nine combinations: three songs against three bodies of text. The output goes to
out/, which is not committed -- it carries the original lyrics beside the
rewrites so the fit can be judged on the page, and those are not ours to
publish.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.dress import Dressing, NeedsAnswer, dress, manual_writer
from hollow.exam import score
from hollow.grade import grade
from hollow.library import Library
from hollow.timing import word_times

OUT = Path("out/nine")
ASK = Path("out/prompts")

# Three songs, chosen to be different to sing: a mid-tempo pop song that came in
# from a YouTube URL, a fast rap with an awkward meter, and a ballad.
SONGS = ["Never Gonna Give You Up", "The statement", "Feel (Stripped)"]
CORPORA = ["ikea-manuals", "yelp-reviews-1star", "legal-disclaimers"]

# The licence each combination is generated at. Varied on purpose so the dial is
# visible across the set rather than described.
LICENCE = {
    ("Never Gonna Give You Up", "ikea-manuals"): 0.0,
    ("Never Gonna Give You Up", "yelp-reviews-1star"): 0.6,
    ("Never Gonna Give You Up", "legal-disclaimers"): 1.0,
    ("The statement", "ikea-manuals"): 0.6,
    ("The statement", "yelp-reviews-1star"): 0.6,
    ("The statement", "legal-disclaimers"): 0.0,
    ("Feel (Stripped)", "ikea-manuals"): 1.0,
    ("Feel (Stripped)", "yelp-reviews-1star"): 0.0,
    ("Feel (Stripped)", "legal-disclaimers"): 0.6,
}


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def page(song, h, originals, d: Dressing, card) -> str:
    """One song, as plain text: the rewrite, with the original beside it."""
    bent = {b.line: b for b in d.bends}
    width = max((len(t) for t in originals), default=40)
    width = min(max(width, 30), 52)
    out = [
        f"{song.title} — {song.artist}",
        f"{d.corpus}, licence {d.licence:.2f}",
        f"came in as: {'a YouTube URL' if song.source_kind == 'youtube' else 'a karaoke file'}",
        "",
        str(card),
        "",
        f"{'ORIGINAL LINE'.ljust(width)}  {'REWRITTEN LINE'}",
        f"{'-' * width}  {'-' * width}",
    ]
    for l, text in zip(h.lines, d.lines):
        left = (originals[l.id] if l.id < len(originals) else "")[:width]
        mark = ""
        if l.id in bent:
            b = bent[l.id]
            mark = f"   ← bent: wanted {b.slots} syllables, got {b.written}"
        elif l.uncertain:
            mark = "   ← timing uncertain, excluded from the score"
        out.append(f"{left.ljust(width)}  {text}{mark}")
    if d.bends:
        out += ["", "WHERE THE TUNE HAD TO BEND", ""]
        out += [f"  line {b.line:2d}: wanted {b.slots} syllables, got {b.written} — {b.why}"
                for b in d.bends]
    else:
        out += ["", "No line had to bend: every one of them has exactly the syllables "
                    "the tune asks for."]
    return "\n".join(out) + "\n"


def sweep(started: float) -> None:
    """Delete questions left over from an earlier shape of a song.

    Re-extracting a song changes its rows, so yesterday's prompt is about a
    line that no longer exists. Leaving it lying next to today's is how you end
    up writing forty lines nothing will ever read.
    """
    for prompt in ASK.rglob("*.prompt.txt"):
        if prompt.stat().st_mtime < started:
            answer = prompt.with_name(prompt.name.replace(".prompt.", ".answer."))
            answer.unlink(missing_ok=True)
            prompt.unlink()


def build(pending_only: bool = False) -> None:
    import time

    started = time.time()
    lib = Library()
    by_title = {s.title: s for s in lib.songs()}
    missing = [t for t in SONGS if t not in by_title]
    if missing:
        raise SystemExit(f"not in the library yet: {missing}")

    OUT.mkdir(parents=True, exist_ok=True)
    rows, waiting = [], 0
    for title in SONGS:
        song = by_title[title]
        h = lib.hollow(song.ref)
        originals = lib.originals(song.ref)
        for corpus in CORPORA:
            licence = LICENCE[(title, corpus)]
            text = Path(f"data/datasets/{corpus}.txt").read_text(encoding="utf-8")
            writer = manual_writer(ASK / f"{slug(title)}-{corpus}-{int(licence * 100)}")
            try:
                d = dress(h, text, licence, corpus_name=corpus, writer=writer,
                          log=lambda *a: None)
            except NeedsAnswer as need:
                waiting += 1
                print(f"  waiting  {title} × {corpus} @ {licence:.2f} — {need}")
                continue
            if pending_only:
                continue
            card = grade(h, d, text, originals)
            name = f"{corpus}-{int(round(licence * 100)):03d}"
            lib.save_dressing(song.ref, name, {
                "name": name, **d.to_dict(), "words": word_times(h, d.lines),
                "card": {"singable": round(card.singable, 2),
                         "unsingable": card.unsingable,
                         "corpus_fidelity": round(card.corpus_fidelity, 3),
                         "corpus_note": card.corpus_note,
                         "register_distance": round(card.register_distance, 2),
                         "register_parts": {k: round(v, 2)
                                            for k, v in card.register_parts.items()},
                         "grammar": round(card.grammar, 3),
                         "grammar_note": card.grammar_note,
                         "bad_lines": card.bad_lines, "honesty": round(card.honesty, 3),
                         "undeclared_bends": card.undeclared_bends,
                         "excluded": card.excluded,
                         "exam": {"fit": round(card.exam.fit, 3),
                                  "stress": round(card.exam.stress, 3),
                                  "rhyme": round(card.exam.rhyme, 3),
                                  "vowel": round(card.exam.vowel, 3)}},
            })
            (OUT / f"{slug(title)}--{corpus}.txt").write_text(
                page(song, h, originals, d, card), encoding="utf-8")
            rows.append((title, corpus, licence, card, d))
            print(f"  {title[:26]:28} {corpus:20} {licence:.2f}  "
                  f"{card.singable:5.2f}/10  corpus {card.corpus_fidelity:4.0%}  "
                  f"parse {card.grammar:4.0%}  bends {len(d.bends):2d}")

    sweep(started)
    if waiting:
        print(f"\n{waiting} combination(s) need a writer. Prompts are under {ASK}/;"
              f"\nwrite the answer next to each .prompt.txt as .answer.txt, then run again.")
    if rows:
        index(rows)


def index(rows) -> None:
    out = ["# The nine", "",
           "| song | text | licence | singability | from the corpus | lines that parse "
           "| register gap | bends |", "|---|---|---|---|---|---|---|---|"]
    for title, corpus, licence, card, d in rows:
        out.append(f"| {title} | {corpus} | {licence:.2f} | {card.singable:.2f} | "
                   f"{card.corpus_fidelity:.0%} | {card.grammar:.0%} | "
                   f"{card.register_distance:.2f} | {len(d.bends)} |")
    (OUT / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}/INDEX.md")


if __name__ == "__main__":
    build(pending_only="--pending" in sys.argv)
