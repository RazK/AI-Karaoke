"""Dress a body of text onto a song.

The one control is licence, a number from 0 to 1.

At 0 the system may only use phrases the corpus already contains, trimmed
lightly -- recognisably IKEA, stilted, funny because it is real. At 1 it may
paraphrase, pad, pun and coin words -- fluent and smooth, but further from what
the corpus actually says. In between it takes a phrase from the corpus when a
good one exists and hands the line to the writer when none does.

Fitting the melody is not on that dial. It is a hard constraint with one escape
hatch: on a line where the corpus genuinely offers no fit, the system may
deviate, and every line where it did is listed. At the faithful end that list is
the most interesting thing the system produces -- it is where the corpus and the
song would not meet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import prosody
from .format import Hollow, Line, render

# Words that can be dropped from either end of a found phrase without it
# stopping being the corpus's own wording.
TRIMMABLE = frozenset(
    "a an the and or but so of to in on at for with is are was were be been "
    "that this it its as if then than very just also now here there".split()
)


@dataclass
class Bend:
    """A line where the melody constraint had to give."""

    line: int
    slots: int
    written: int
    why: str

    def __str__(self) -> str:
        # A bend is not always a syllable miscount -- a line can have exactly
        # the right number and still sit wrong on the stresses. Saying "wanted
        # 10, got 10" for one of those reads like nothing is wrong at all.
        count = (f"wanted {self.slots} syllables, got {self.written}"
                 if self.written != self.slots else
                 f"{self.slots} syllables, which is right")
        return f"line {self.line}: {count} — {self.why}"


@dataclass
class Dressing:
    licence: float
    corpus: str
    lines: list[str]
    bends: list[Bend] = field(default_factory=list)
    from_corpus: list[bool] = field(default_factory=list)  # per line: found, not written

    def to_dict(self) -> dict:
        return {
            "licence": self.licence,
            "corpus": self.corpus,
            "lines": self.lines,
            "bends": [b.__dict__ for b in self.bends],
            "from_corpus": self.from_corpus,
        }


# ── the corpus, as a searchable run of words ───────────────────────────────

@dataclass
class Corpus:
    words: list[str]
    syls: list[list[prosody.Syl]]
    syllables: list[int]  # syllable count per word
    starts: set[int]  # word indices that begin a sentence
    ends: set[int]  # word indices that end one

    @staticmethod
    def build(text: str) -> "Corpus":
        words, starts, ends, at_start = [], set(), set(), True
        for token in re.findall(r"[A-Za-z][A-Za-z'’\-]*|[.!?;:,]", text):
            if token[0].isalpha():
                if at_start:
                    starts.add(len(words))
                    at_start = False
                words.append(token)
            elif words:
                ends.add(len(words) - 1)
                at_start = token in ".!?;:"
        syls = [list(prosody.pronunciations(w)[0]) for w in words]
        return Corpus(
            words=words,
            syls=syls,
            syllables=[len(s) for s in syls],
            starts=starts,
            ends=ends,
        )

    def phrase(self, i: int, j: int) -> str:
        """The corpus's own words, with shouting turned down to sentence case."""
        ws = [w.lower() if w.isupper() and len(w) > 1 else w for w in self.words[i:j]]
        out = " ".join(ws)
        return out[0].upper() + out[1:] if out else out


@dataclass
class Candidate:
    i: int
    j: int
    text: str
    n: int
    stress_fit: float
    score: float


def _trim(c: Corpus, i: int, j: int, want: int) -> tuple[int, int]:
    """Drop trimmable words off either end while that gets us closer to `want`."""
    total = sum(c.syllables[i:j])
    while total > want and j > i + 1 and c.words[j - 1].lower() in TRIMMABLE:
        j -= 1
        total -= c.syllables[j]
    while total > want and j > i + 1 and c.words[i].lower() in TRIMMABLE:
        total -= c.syllables[i]
        i += 1
    return i, j


def find(c: Corpus, line: Line, near: float, used: set[int]) -> list[Candidate]:
    """Every phrase in the corpus that could stand in for this line.

    `near` is where in the corpus we would like to be, from 0 to 1, so that the
    rewrite walks through the source text roughly in its own order instead of
    ransacking one good paragraph.
    """
    want = len(line.slots)
    asks = [s.stress for s in line.slots]
    held = [s.held for s in line.slots]
    home = near * max(len(c.words) - 1, 1)
    out: list[Candidate] = []

    for i in range(len(c.words)):
        total, j = 0, i
        while j < len(c.words) and total < want + 3:
            total += c.syllables[j]
            j += 1
            if total < want - 3:
                continue
            a, b = _trim(c, i, j, want)
            n = sum(c.syllables[a:b])
            if abs(n - want) > 3 or b <= a:
                continue
            syls = [x for k in range(a, b) for x in c.syls[k]]
            overlap = min(len(syls), want)
            hits = sum(syls[k].stressed == asks[k] for k in range(overlap))
            stress_fit = hits / max(want, len(syls))
            unholdable = sum(
                1 for k in range(overlap) if held[k] and not syls[k].can_hold
            )
            score = (
                -6.0 * abs(n - want)          # fitting the melody dominates
                + 3.0 * stress_fit
                - 0.6 * unholdable
                + (0.5 if a in c.starts else 0)
                + (0.7 if b - 1 in c.ends else 0)
                # a phrase that opens or closes on a dangling "of" reads as a
                # fragment cut out of something, which it is
                - (0.9 if c.words[a].lower() in TRIMMABLE and a not in c.starts else 0)
                - (0.9 if c.words[b - 1].lower() in TRIMMABLE else 0)
                # running through the end of one sentence and into the next is
                # how you get "would not close The chef at": it fits the melody
                # and is not English
                - 2.5 * len(c.ends & set(range(a, b - 1)))
                - 1.2 * len(used & set(range(a, b))) / max(b - a, 1)
                - 1.5 * abs((a + b) / 2 - home) / max(len(c.words), 1)
            )
            out.append(Candidate(a, b, c.phrase(a, b), n, stress_fit, score))
    out.sort(key=lambda x: -x.score)
    seen, uniq = set(), []
    for x in out:  # the same phrase can be reached by trimming from either side
        if x.text.lower() not in seen:
            seen.add(x.text.lower())
            uniq.append(x)
    return uniq[:40]


# ── the writer ─────────────────────────────────────────────────────────────

PROMPT = """\
You are writing new words for a song. You are given the song's shape and
nothing else -- no melody name, no original words, and you do not need them.

Each row below is one line of the song. Each slot takes exactly one written
syllable.
  ●  stressed slot          ○  unstressed slot
  _  the slot before it is held long: it needs an open vowel that can be
     sustained, not a schwa and not a syllable closed by t/d/k/p/b/g
  [A] rows sharing a letter must rhyme with each other at the line ending

{legend}

THE SOURCE TEXT you are rewriting into the song:
---
{corpus}
---

LICENCE: {licence:.2f} out of 1.
{licence_note}

RULES
- Write only the {n} rows marked "<- write this one". Rows marked ALREADY
  WRITTEN are done; leave them alone, but make your lines sit naturally beside
  them.
- Answer one row per output line, each prefixed with its row number, like:
      L07: your words for that row
  Nothing else. No commentary, no blank lines, no numbering of your own.
- Each line must have exactly the number of syllables its row asks for. This is
  not a preference. A line one syllable out is audibly wrong.
- Put stressed syllables on ● and unstressed on ○.
- A slot marked _ is held long. Put an open vowel there -- not a schwa, not a
  syllable ending in t/d/k/p/b/g.
- Lines sharing a rhyme letter must rhyme with each other.
- Every line must read as English on its own.

Write those {n} rows now."""

FAITHFUL = """\
Stay close to the source. Prefer its own words and phrases. You may drop words
and change word endings. Do not invent imagery the source does not contain."""

MIDDLE = """\
Keep the source's subject and voice. You may rearrange it, paraphrase, and
choose different words for the same thing where the syllables demand it."""

INVENTIVE = """\
Take what you like from the source's subject and run with it. Paraphrase
freely, pad, pun, and coin portmanteaus where they make a line sing."""


def _note(licence: float) -> str:
    return FAITHFUL if licence < 0.34 else MIDDLE if licence < 0.67 else INVENTIVE


def _repair(text: str, want: int) -> str:
    """Cheap local fixes before going back to the writer.

    Dropping a filler word or opening a contraction moves a line by one
    syllable, which is the amount it is usually out by.
    """
    for _ in range(3):
        n = len(prosody.syllables_for(text, want))
        if n == want:
            return text
        ws = text.split()
        if n > want:
            for k, w in enumerate(ws):
                if w.lower().strip(",.") in TRIMMABLE and len(ws) > 2:
                    text = " ".join(ws[:k] + ws[k + 1 :])
                    break
            else:
                for long, short in (("do not", "don't"), ("it is", "it's"),
                                    ("cannot", "can't"), ("will not", "won't"),
                                    ("you are", "you're"), ("we are", "we're")):
                    if long in text.lower():
                        text = re.sub(long, short, text, flags=re.I)
                        break
                else:
                    return text
        else:
            for short, long in (("don't", "do not"), ("it's", "it is"),
                                ("can't", "cannot"), ("won't", "will not"),
                                ("you're", "you are"), ("we're", "we are")):
                if short in text.lower():
                    text = re.sub(short, long, text, flags=re.I)
                    break
            else:
                return text
    return text


# ── where the writing comes from ───────────────────────────────────────────

class NeedsAnswer(Exception):
    """A manual writer was asked something and has not answered yet."""


def anthropic_writer(model: str = "claude-opus-5"):
    """The writer, over the API. The key comes from the environment.

    What goes over the wire is a word-free HOLLOW rendering and a corpus the
    user supplied. No copyrighted lyric is ever part of it.
    """
    import os

    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def ask(prompt: str) -> str:
        r = client.messages.create(
            model=model, max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text

    return ask


def manual_writer(dir_path):
    """A writer who is a person (or an agent) at a keyboard.

    Each question is written to a file. If the answer file is not there yet the
    caller is told to come back. This is how the shipped songs were written
    without an API key, and it is also the honest test of the format: whoever
    answers has only ever seen the word-free rows.
    """
    from pathlib import Path

    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)

    def ask(prompt: str) -> str:
        import hashlib

        key = hashlib.md5(prompt.encode()).hexdigest()[:10]
        q, a = d / f"{key}.prompt.txt", d / f"{key}.answer.txt"
        # Always rewrite the question, answered or not, so that a caller can
        # tell this run's questions from ones left over by an earlier shape of
        # the song.
        q.write_text(prompt, encoding="utf-8")
        if a.exists():
            return a.read_text(encoding="utf-8")
        raise NeedsAnswer(f"answer needed: write {a}")

    return ask


# ── the run ────────────────────────────────────────────────────────────────

def _rows(h: Hollow, group: int, filled: dict[int, str]) -> str:
    """The group's rows, with the lines already found shown in place."""
    out = []
    for lid in h.groups[group]:
        l = h.lines[lid]
        row = " ".join(("●" if s.stress else "○") + ("_" if s.held else "")
                       for s in l.slots)
        head = f"L{lid:02d} [{l.rhyme}] {len(l.slots):2d}  {row}"
        out.append(f"{head}   ALREADY WRITTEN: {filled[lid]}" if lid in filled
                   else f"{head}   <- write this one")
    return "\n".join(out)


_ANSWER = re.compile(r"^\s*L?(\d+)\s*[:.\)]\s*(.+?)\s*$", re.M)


def dress(
    h: Hollow,
    corpus_text: str,
    licence: float,
    *,
    corpus_name: str = "",
    writer=None,
    log=print,
) -> Dressing:
    """Put `corpus_text` onto the song at the given licence."""
    licence = max(0.0, min(1.0, float(licence)))
    c = Corpus.build(corpus_text)
    if not c.words:
        raise ValueError("that text has no words in it")

    # The bar a phrase lifted straight from the corpus has to clear. It rises
    # with licence: the more freedom the writer has, the pickier we are about
    # taking someone else's sentence instead.
    bar = 0.55 + 0.45 * licence

    partner = {b: a for a, b in h.rhyme_pairs}
    found: dict[int, Candidate] = {}
    used: set[int] = set()

    for k, line in enumerate(h.lines):
        cands = find(c, line, k / max(len(h.lines) - 1, 1), used)
        if not cands:
            continue
        mate = partner.get(line.id)
        if mate in found:  # keep the rhyme if any candidate offers it
            want_rhyme = [x for x in cands if prosody.rhymes(x.text, found[mate].text)]
            cands = want_rhyme or cands
        best = cands[0]
        if best.n == len(line.slots) and best.stress_fit >= bar:
            found[line.id] = best
            used.update(range(best.i, best.j))

    lines: dict[int, str] = {lid: x.text for lid, x in found.items()}
    log(f"licence {licence:.2f}: {len(lines)}/{len(h.lines)} lines found in the corpus")

    # Everything still empty goes to the writer, a phrase group at a time so it
    # can see what its lines have to sit next to. At licence 0 there is no
    # writer: the corpus's own phrases are the whole of the output, and a line
    # they cannot fill is a bend worth knowing about.
    missing = [l.id for l in h.lines if l.id not in lines]
    unanswered: list[str] = []
    if missing and writer is not None and licence > 0:
        for gi, ids in enumerate(h.groups):
            gap = [i for i in ids if i not in lines]
            if not gap:
                continue
            prompt = PROMPT.format(
                legend=_rows(h, gi, lines), corpus=corpus_text.strip()[:6000],
                licence=licence, licence_note=_note(licence), n=len(gap),
            )
            try:
                reply = writer(prompt)
            except NeedsAnswer as need:
                # Keep going so that one run puts every question on the table
                # rather than one per attempt.
                unanswered.append(str(need))
                continue
            for m in _ANSWER.finditer(reply):
                lid = int(m.group(1))
                if lid in gap:
                    lines[lid] = m.group(2).strip(' "')
    if unanswered:
        raise NeedsAnswer("\n".join(unanswered))

    # Anything the writer did not answer, and everything at licence 0, falls
    # back to the closest phrase the corpus has. The song always plays.
    bends: list[Bend] = []
    fell_back: set[int] = set()
    for k, line in enumerate(h.lines):
        want = len(line.slots)
        if line.id not in lines:
            cands = find(c, line, k / max(len(h.lines) - 1, 1), used)
            if not cands:
                lines[line.id] = "…"
                bends.append(Bend(line.id, want, 0, "the corpus has nothing this size"))
                continue
            lines[line.id] = cands[0].text
            fell_back.add(line.id)
            used.update(range(cands[0].i, cands[0].j))

        lines[line.id] = _repair(lines[line.id], want)
        got = len(prosody.syllables_for(lines[line.id], want))
        if got != want:
            bends.append(Bend(
                line.id, want, got,
                "no phrase in the corpus is this length"
                if line.id in fell_back else "the writer could not land it",
            ))
        elif line.id in fell_back:
            # The syllables landed, but only because we took the nearest phrase
            # the corpus had rather than one that actually fits the line: its
            # stresses fall in the wrong places. That is a deviation and it gets
            # declared, because a line of the right length with the stress in
            # the wrong place is audibly wrong, and this list is where the
            # corpus and the song genuinely would not meet.
            bends.append(Bend(line.id, want, got,
                              "nothing in the corpus fits this line's stresses"))

    ordered = [lines[l.id] for l in h.lines]
    return Dressing(
        licence=licence,
        corpus=corpus_name,
        lines=ordered,
        bends=bends,
        from_corpus=[l.id in found for l in h.lines],
    )
