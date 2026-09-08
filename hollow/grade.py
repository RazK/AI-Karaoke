"""The card Raz reads after a song is dressed.

Singability is a gate, not an ingredient. Below seven out of ten the song is
marked unsingable and nothing else about it is reported, because a song nobody
can sing has no comedy value and no fidelity worth discussing.

Above the gate there are four more numbers, side by side. None of them is
averaged into another and none is averaged into the singability score. They
measure different things and collapsing them into one number would throw away
the only information worth having.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import prosody
from .dress import Dressing
from .exam import Score, score
from .format import Hollow

GATE = 7.0

# Closed-class words. A line that ends on one is almost always a fragment.
FUNCTION = frozenset(
    "a an the and or but nor so yet for of to in on at by with from into onto "
    "over under about as if than that this these those is are was were be been "
    "being am do does did have has had will would can could shall should may "
    "might must not no i you he she it we they me him her us them my your his "
    "its our their there here when while because although though very just".split()
)
DANGLING = FUNCTION - {"no", "not", "there", "here", "it", "me", "you", "us", "them", "him", "her"}


@dataclass
class Card:
    singable: float
    exam: Score
    unsingable: bool
    corpus_fidelity: float = 0.0
    corpus_note: str = ""
    register_distance: float = 0.0
    register_parts: dict = field(default_factory=dict)
    grammar: float = 0.0
    grammar_note: str = ""
    bad_lines: list[int] = field(default_factory=list)
    declared_bends: int = 0
    undeclared_bends: list[int] = field(default_factory=list)
    honesty: float = 1.0
    excluded: list[int] = field(default_factory=list)

    def __str__(self) -> str:
        if self.unsingable:
            return (f"UNSINGABLE — {self.singable:.2f}/10, below the gate of {GATE}.\n"
                    "Nothing else is reported: a song nobody can sing has no comedy\n"
                    "value and no fidelity worth discussing.")
        return "\n".join([
            f"  singability      {self.singable:5.2f}/10   (gate {GATE}, passed)",
            f"  from the corpus  {self.corpus_fidelity:5.0%}      {self.corpus_note}",
            f"  register gap     {self.register_distance:5.2f}      "
            + ", ".join(f"{k} {v:+.2f}" for k, v in self.register_parts.items()),
            f"  lines that parse {self.grammar:5.0%}      {self.grammar_note}"
            + (f"  bad: {self.bad_lines}" if self.bad_lines else ""),
            f"  bend honesty     {self.honesty:5.2f}      {self.declared_bends} declared, "
            f"{len(self.undeclared_bends)} undeclared"
            + (f" {self.undeclared_bends}" if self.undeclared_bends else ""),
        ] + ([f"  excluded         {len(self.excluded)} lines the aligner was unsure of"]
             if self.excluded else []))


# ── how much of this is really the corpus ──────────────────────────────────

def corpus_fidelity(lines: list[str], corpus_text: str) -> tuple[float, str]:
    """Share of written words sitting inside a run of two or more that the
    source text actually contains.

    Single words in common are not evidence of anything -- everyone writes
    "the". A run of two or more is a phrase that came from somewhere.
    """
    src = [w.lower() for w in prosody.words(corpus_text)]
    grams: dict[int, set[tuple[str, ...]]] = {}
    for n in range(2, 9):
        grams[n] = {tuple(src[i : i + n]) for i in range(len(src) - n + 1)}

    covered = total = 0
    longest = 0
    for line in lines:
        ws = [w.lower() for w in prosody.words(line)]
        total += len(ws)
        i = 0
        while i < len(ws):
            best = 0
            for n in range(min(8, len(ws) - i), 1, -1):
                if tuple(ws[i : i + n]) in grams[n]:
                    best = n
                    break
            if best:
                covered += best
                longest = max(longest, best)
                i += best
            else:
                i += 1
    share = covered / total if total else 0.0
    return share, f"({covered}/{total} words in runs from the source, longest run {longest})"


# ── how far the corpus sits from the song ──────────────────────────────────

def _features(text: str) -> dict[str, float]:
    ws = prosody.words(text)
    if not ws:
        return {}
    low = [w.lower() for w in ws]
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    return {
        "word length": sum(len(prosody.pronunciations(w)[0]) for w in ws) / len(ws),
        "function words": sum(w in FUNCTION for w in low) / len(ws),
        "vocabulary": len(set(low)) / len(ws),
        "sentence length": len(ws) / sentences,
        "numbers": len(re.findall(r"\d", text)) / max(len(text), 1) * 100,
    }


# Plausible spread of each feature across ordinary English, used to put the
# five on one scale. They are not fitted to anything; they are round numbers
# chosen so that a difference of 1.0 means "about as different as English gets".
_SPREAD = {"word length": 0.6, "function words": 0.25, "vocabulary": 0.35,
           "sentence length": 12.0, "numbers": 2.0}


def register_distance(corpus_text: str, original: list[str]) -> tuple[float, dict]:
    """How far the corpus's register sits from the song's.

    This is the whole point of the product and the hardest thing here to
    measure. The proxy is five surface features -- how long the words are, how
    much of the text is function words, how varied the vocabulary is, how long
    the sentences run, and how numerical it is -- each divided by a fixed
    spread so they land on one scale, then averaged.

    Say plainly what it does not do: it measures lexical and syntactic register,
    not tone, not subject matter, and not whether the joke lands. A furious
    restaurant review and an ecstatic one would score alike.

    The song's own words are read here, on this machine, and go nowhere.
    """
    a, b = _features(corpus_text), _features("\n".join(original))
    if not a or not b:
        return 0.0, {}
    parts = {k: (a[k] - b[k]) / _SPREAD[k] for k in a}
    return sum(abs(v) for v in parts.values()) / len(parts), parts


# ── does each line parse as English on its own ─────────────────────────────

JUDGE = """\
Below are {n} lines from a song lyric. Judge each one on its own, as a piece of
English: could a person say or sing this line and have it read as a phrase,
rather than as words cut out of the middle of a sentence?

Fragments are fine if they stand up ("Under the kitchen table", "No name").
What fails is a line that runs through a boundary and stops meaning anything
("would not close The chef at", "Flush with the surface Step of").

Answer one line per row, exactly "<number>: yes" or "<number>: no". Nothing else.

{lines}"""


def _looks_like_a_fragment(line: str) -> bool:
    ws = [w.lower() for w in prosody.words(line)]
    if not ws:
        return True
    return ws[-1] in DANGLING or (len(ws) > 1 and ws[0] in DANGLING - {"the", "a", "an", "and", "but", "so", "no", "not"})


def grammar(lines: list[str], writer=None) -> tuple[float, list[int], str]:
    """Fraction of lines that parse as English on their own.

    Grade lines, not songs: a line can fit the melody perfectly and still be a
    failure. Only the rewritten lines are shown to the judge, never the song.
    """
    if writer is not None:
        numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(lines))
        try:
            reply = writer(JUDGE.format(n=len(lines), lines=numbered))
            verdicts = {int(m.group(1)): m.group(2).lower().startswith("y")
                        for m in re.finditer(r"^\s*(\d+)\s*:\s*(\w+)", reply, re.M)}
            if len(verdicts) >= 0.8 * len(lines):
                bad = [i for i in range(len(lines)) if not verdicts.get(i, True)]
                return 1 - len(bad) / len(lines), bad, "judged line by line by the writer"
        except Exception:
            pass
    bad = [i for i, t in enumerate(lines) if _looks_like_a_fragment(t)]
    return (1 - len(bad) / len(lines), bad,
            "local check only: catches lines that dangle on a function word")


# ── was the bend list honest ───────────────────────────────────────────────

def honesty(h: Hollow, d: Dressing) -> tuple[float, int, list[int]]:
    """Check the declared bends against what actually happened.

    An undeclared bend is worse than a declared one, and costs more.
    """
    declared = {b.line for b in d.bends}
    # What actually happened, recomputed from scratch: a line of the wrong
    # length, or one whose stresses fall further out than the licence allows.
    bar = 0.55 + 0.45 * d.licence
    actual = set()
    for line, text in zip(h.lines, d.lines):
        if line.uncertain:
            continue
        syls = prosody.syllables_for(text, len(line.slots))
        n = len(line.slots)
        if len(syls) != n:
            actual.add(line.id)
            continue
        hit = sum(s.stressed == slot.stress for s, slot in zip(syls, line.slots))
        if hit / max(n, len(syls)) < bar:
            actual.add(line.id)
    undeclared = sorted(actual - declared)
    n = max(len(h.lines), 1)
    return max(0.0, 1 - (len(declared & actual) / n) - 3.0 * len(undeclared) / n), len(declared), undeclared


def grade(h: Hollow, d: Dressing, corpus_text: str, original: list[str],
          writer=None) -> Card:
    s = score(h, d.lines)
    if s.score < GATE:
        return Card(singable=s.score, exam=s, unsingable=True, excluded=s.excluded)

    fid, note = corpus_fidelity(d.lines, corpus_text)
    dist, parts = register_distance(corpus_text, original)
    gram, bad, gnote = grammar(d.lines, writer)
    hon, declared, undeclared = honesty(h, d)
    return Card(
        singable=s.score, exam=s, unsingable=False,
        corpus_fidelity=fid, corpus_note=note,
        register_distance=dist, register_parts=parts,
        grammar=gram, grammar_note=gnote, bad_lines=bad,
        declared_bends=declared, undeclared_bends=undeclared, honesty=hon,
        excluded=s.excluded,
    )
