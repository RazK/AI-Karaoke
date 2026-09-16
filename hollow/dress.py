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
    # per line: this line's words are the corpus's own, not written for it
    from_corpus: list[bool] = field(default_factory=list)
    section: list[int] = field(default_factory=list)  # which section each line is in
    # per line: the earlier line it copies, when it is a repeat of one
    echo_of: list[int | None] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "licence": self.licence,
            "corpus": self.corpus,
            "lines": self.lines,
            "bends": [b.__dict__ for b in self.bends],
            "from_corpus": self.from_corpus,
            "section": self.section,
            "echo_of": self.echo_of,
        }


# ── the corpus, as a searchable run of words ───────────────────────────────

def _is_furniture(block: str) -> bool:
    """Is this block a label rather than something anyone would sing?

    "REVIEW 3 - Rating: 1 star", "Reviewer: NeverComingBack Mark", "PARTS LIST".
    Left in, they get sung: one chorus came out as "Rating one star Reviewer"
    three times over, which is the corpus's filing system, not its voice.
    """
    words = re.findall(r"[A-Za-z][A-Za-z'’\-]*", block)
    if len(words) >= 8:
        return False
    stripped = block.strip()
    return ":" in stripped or stripped.isupper()


_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("_ _ twenty thirty forty fifty sixty seventy eighty ninety").split()


def _say(number: str) -> list[str]:
    """Numbers as words, because a number is sung, not printed.

    The source texts are full of them -- "Step 1 of 18", "Screw, 5x50mm",
    "Panel A x2" -- and dropping them turned every instruction into "Step of".
    """
    n = int(number)
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        tens, ones = divmod(n, 10)
        return [_TENS[tens]] + ([_ONES[ones]] if ones else [])
    return [w for digit in number for w in _say(digit)]


@dataclass
class Corpus:
    words: list[str]
    syls: list[list[prosody.Syl]]
    syllables: list[int]  # syllable count per word
    starts: set[int]  # word indices that begin a sentence
    ends: set[int]  # word indices that end one
    # Word ranges of the source's own paragraphs. These carry the text's order:
    # "Step 1 of 18" then "Step 2 of 18", one review's complaint then the next.
    # Drawing a whole section of the song from one stretch of them is what makes
    # consecutive lines about the same thing.
    paras: list[tuple[int, int]] = field(default_factory=list)

    @staticmethod
    def build(text: str) -> "Corpus":
        words, starts, ends, at_start = [], set(), set(), True
        paras: list[tuple[int, int]] = []
        for block in text.split("\n\n"):
            if _is_furniture(block):
                continue
            first = len(words)
            # A line of a list ends a thought even without a full stop. Without
            # this, a span runs off the end of one item and into the next --
            # "C between the two assembled side" -- which fits the tune and is
            # not a sentence.
            block = re.sub(r"\n(?=\s*\S)", ".\n", block)
            for token in re.findall(r"[A-Za-z][A-Za-z'’\-]*|\d+|[.!?;:,]", block):
                if token[0].isalpha() or token[0].isdigit():
                    spoken = _say(token) if token[0].isdigit() else [token]
                    if at_start:
                        starts.add(len(words))
                        at_start = False
                    words.extend(spoken)
                elif words:
                    ends.add(len(words) - 1)
                    at_start = token in ".!?;:"
            if len(words) > first:
                paras.append((first, len(words)))
                ends.add(len(words) - 1)  # a paragraph ends a sentence
                at_start = True
        syls = [list(prosody.pronunciations(w)[0]) for w in words]
        return Corpus(
            words=words,
            syls=syls,
            syllables=[len(s) for s in syls],
            starts=starts,
            ends=ends,
            paras=paras,
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


def _cliff(c: Corpus, a: int, b: int) -> bool:
    """Does this span end on a word still waiting for the one after it?"""
    tail = " ".join(w.lower() for w in c.words[max(a, b - 3):b])
    return any(tail.endswith(x) for x in TRAILING)


def find(c: Corpus, line: Line, used: set[int],
         window: tuple[int, int] | None = None) -> list[Candidate]:
    """Every phrase in the corpus that could stand in for this line.

    `window` is the stretch of the source this part of the song is drawn from.
    Searching the whole text for every line independently is what produced a
    song whose seventh line was about a cam lock and whose eighth was about a
    hair in the soup: each line fitted and the song meant nothing.
    """
    want = len(line.slots)
    asks = [s.stress for s in line.slots]
    held = [s.held for s in line.slots]
    lo, hi = window or (0, len(c.words))
    home = (lo + hi) / 2
    out: list[Candidate] = []

    for i in range(lo, hi):
        total, j = 0, i
        while j < hi and total < want + 3:
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
                # Landing where the source itself starts and stops is worth
                # far more than it used to be: a span that ends mid-noun-phrase
                # ("Insert cam lock bolts into the pre-drilled") fits the tune
                # and is half a sentence. There is no way to know a noun ends
                # here, but there is a way to know the source stopped here.
                + (0.8 if a in c.starts else 0)
                + (1.5 if b - 1 in c.ends else 0)
                # a phrase that opens or closes on a dangling "of" reads as a
                # fragment cut out of something, which it is
                # A leading "The" is ordinary English; a leading "Of" is the
                # middle of a sentence with its front cut off.
                - (3.0 if c.words[a].lower() in prosody.BAD_OPENER
                   and a not in c.starts else 0)
                # "took so long that both of my" fits the tune and is not a
                # sentence. grade.py marks these; the engine should not make
                # them in the first place, and both read the same word list.
                - (3.0 if c.words[b - 1].lower() in prosody.DANGLING else 0)
                # running through the end of one sentence and into the next is
                # how you get "would not close The chef at": it fits the melody
                # and is not English
                # Running through the end of one sentence and into the next is
                # how "Step one of eighteen Lay" happens: it fits the tune, it
                # is two halves of two different instructions, and it was only
                # costing 2.5 against a 6.0 syllable miss, so it kept winning.
                - 6.0 * len(c.ends & set(range(a, b - 1)))
                # A phrase that ends on a quantifier whose noun is in the next
                # sentence: "I have spent less on a full".
                - (3.0 if _cliff(c, a, b) else 0)
                - 1.2 * len(used & set(range(a, b))) / max(b - a, 1)
                - 1.5 * abs((a + b) / 2 - home) / max(hi - lo, 1)
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
- Every line must be a whole thought that can be read on its own. Never hand
  back a sentence with its front or its end cut off to make the count: no line
  may open on a preposition, end on a preposition, article, conjunction or
  auxiliary verb, or end on "so much" / "one of" with the thing it counts
  missing. Say something shorter and complete instead.
- Write any number as the words someone would sing, and only when it belongs in
  a line. "One eight zero" and "Two zero zero nine" are not English.

Write those {n} rows now."""

REPAIR = """\

These rows came back wrong. The syllable counts below were done by a
pronouncing dictionary on the words you wrote, so they are not up for
argument. Rewrite only these rows, same rules as before, one per line,
prefixed with the row number.

{rows}
"""

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

# Phrases that leave a line on a cliff: the quantifier arrives and the thing it
# counts never does. "My wife's pasta had so much" is a sentence cut to length.
TRAILING = (
    "so much", "so many", "such a", "a lot of", "one of", "kind of", "sort of",
    "out of", "much of", "plenty of", "full of", "none of", "most of",
    "part of", "instead of", "because of", "in front of", "each of", "some of",
    "all of", "as much", "as many", "more of", "rest of", "a full", "a whole",
    "a single", "a real", "the same", "the whole", "the entire", "a bit",
)
# A line may open on "And" -- songs do it constantly. A line may not open on a
# preposition: that is a sentence with its front cut off.
STRANDED = prosody.BAD_OPENER - {"and", "or", "but", "nor", "so", "yet",
                                 "because", "although", "though", "while", "when"}


def ragged(text: str) -> str:
    """Why this line cannot be read on its own, or "" when it can.

    The writer is told to write English and mostly does, but under a syllable
    count it will chop a sentence and hand back the half that fits. Saying so
    costs nothing here and one short paid round to fix.
    """
    words = re.findall(r"[a-z']+", text.lower())
    if not words:
        return "it is empty"
    if words[0] in STRANDED:
        return f"it opens on {words[0]!r}, so it needs words before it that are not there"
    if words[-1] in prosody.DANGLING:
        return f"it ends on {words[-1]!r}, so it needs words after it that are not there"
    joined = " ".join(words)
    for phrase in TRAILING:
        if joined.endswith(phrase):
            return f"it ends on {phrase!r} and the thing it counts never arrives"
    return ""


class NeedsAnswer(Exception):
    """A manual writer was asked something and has not answered yet."""


# What the two models cost per million tokens, in and out, so a run can say
# what it spent instead of guessing.
RATES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def anthropic_writer(model: str = "claude-opus-5", effort: str = "low"):
    """The writer, over the API. The key comes from the environment.

    What goes over the wire is a word-free HOLLOW rendering and a corpus the
    user supplied. No copyrighted lyric is ever part of it.

    `effort` is the price dial, not `model`. Opus thinks before it answers
    whether you ask it to or not, and that thinking is billed as output, so
    effort moves the bill further than the choice of model does. Running totals
    hang off `ask.usage` so the caller can stop before it spends the budget.
    """
    import os

    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    usage = {"model": model, "effort": effort, "calls": 0, "in": 0, "out": 0}

    def ask(prompt: str) -> str:
        r = client.messages.create(
            model=model, max_tokens=16000,
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
        )
        usage["calls"] += 1
        usage["in"] += r.usage.input_tokens
        usage["out"] += r.usage.output_tokens
        # The first block can be a thinking block, which has no text.
        return "".join(b.text for b in r.content if b.type == "text")

    ask.usage = usage
    return ask


def spent(usage: dict) -> float:
    """What a writer's tokens cost, in dollars."""
    rate_in, rate_out = RATES.get(usage.get("model", ""), (0.0, 0.0))
    return (usage.get("in", 0) * rate_in + usage.get("out", 0) * rate_out) / 1e6


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

# ── one section at a time ──────────────────────────────────────────────────
#
# The old engine walked the song line by line and searched the whole corpus for
# each line on its own. Every line fitted and the song meant nothing, because
# line seven came from a paragraph about a cam lock and line eight from a
# paragraph about a hair in the soup. A song is written a part at a time, out of
# one stretch of source, with the lines already written in view.

# At or below this the corpus's own words are the whole output and no model is
# called. Above it, lines the corpus cannot fill go to the writer.
QUOTE_END = 0.20
# At and above this the writer writes every line of a section, and the corpus
# is there for its subject and its voice rather than its sentences.
REPHRASE_START = 0.75
BEAM_WIDTH = 8
CANDIDATES_PER_LINE = 12


def rewrite_share(licence: float) -> float:
    """How much of a section goes to the writer rather than being quoted.

    The old rule was "ask the writer for the lines the corpus cannot fill", and
    the corpus can nearly always fill a line with something, so the top of the
    dial did almost nothing: 1.00 came back looking like 0.00. The dial has to
    hand lines over on purpose. It gives away the worst-fitting quotes first,
    so what stays quoted is what the source said well.
    """
    if licence <= QUOTE_END:
        return 0.0
    if licence >= REPHRASE_START:
        return 1.0
    return (licence - QUOTE_END) / (REPHRASE_START - QUOTE_END)


def stress_bar(licence: float) -> float:
    """How well a lifted phrase's stresses must match before it is accepted.

    It rises with licence: the more freedom the writer has, the less reason to
    take someone else's sentence that only half fits. At 0.75 it reaches 1 and
    nothing is lifted unless it fits perfectly.

    `grade.honesty` needs the same rule to decide what counts as a bend, so it
    lives here and is imported there rather than written out twice.
    """
    return min(1.0, 0.55 + 0.6 * licence)


def _windows(c: Corpus, sizes: list[int]) -> list[tuple[int, int]]:
    """Give each section its own stretch of the source, in the source's order.

    A section's lines then come from neighbouring sentences, which is the whole
    mechanism behind consecutive lines being about the same thing.
    """
    paras = c.paras or [(0, len(c.words))]
    total = sum(sizes) or 1
    out, at = [], 0
    for k, size in enumerate(sizes):
        take = max(1, round(len(paras) * size / total))
        if k == len(sizes) - 1:
            take = max(1, len(paras) - at)
        chunk = paras[at : at + take] or [paras[min(at, len(paras) - 1)]]
        out.append((chunk[0][0], chunk[-1][1]))
        at = min(at + take, len(paras) - 1)
    return out


def _beam(c: Corpus, h: Hollow, ids: list[int], window: tuple[int, int],
          used: set[int]) -> list[Candidate | None]:
    """Choose phrases for a whole section at once, in the source's order.

    Greedy per-line choice is what produced the non-sequiturs: each line took
    the best phrase anywhere and the section wandered. Here a section is one
    search, and a phrase that carries on from the previous line's phrase is
    worth more than a better-fitting phrase from somewhere else.
    """
    lo, hi = window
    span = max(hi - lo, 1)
    partner = {b: a for a, b in h.rhyme_pairs}
    # (total score, last span end, picks)
    beams: list[tuple[float, int, list[Candidate | None]]] = [(0.0, lo, [])]

    for pos, lid in enumerate(ids):
        line = h.lines[lid]
        cands = find(c, line, used, window)[:CANDIDATES_PER_LINE]
        if not cands:
            beams = [(sc, end, picks + [None]) for sc, end, picks in beams]
            continue
        nxt: list[tuple[float, int, list[Candidate | None]]] = []
        for sc, end, picks in beams:
            mate = partner.get(lid)
            rhyme_with = None
            if mate in ids:
                got = picks[ids.index(mate)] if ids.index(mate) < len(picks) else None
                rhyme_with = got.text if got else None
            # Say a thing once per section. A chorus that sings "my wife's
            # pasta had so much" three times over is the search finding one good
            # phrase and stopping.
            #
            # This is a rule, and rules come before preferences: rhyme used to
            # be applied first, and on three lines that rhyme with each other it
            # narrowed the choice to the single phrase already used, so the
            # fallback handed that same phrase back three times.
            taken = {x.text.lower() for x in picks if x}
            pool = [x for x in cands if x.text.lower() not in taken] or cands
            if rhyme_with:
                want = [x for x in pool if prosody.rhymes(x.text, rhyme_with)]
                pool = want or pool
            spans = {k for x in picks if x for k in range(x.i, x.j)}
            for cand in pool:
                gap = cand.i - end
                step = cand.score
                step += 2.0 if gap >= 0 else 0.0           # source order
                step += 1.5 if 0 <= gap <= 4 else 0.0      # carries straight on
                step -= 3.0 * abs(gap) / span              # jumping about
                # A chorus that sings "my wife's pasta had so much" three times
                # over is not a chorus, it is the search finding one good phrase
                # and stopping. Inside a section, say a thing once.
                step -= 4.0 * len(spans & set(range(cand.i, cand.j))) / max(cand.j - cand.i, 1)
                nxt.append((sc + step, cand.j, picks + [cand]))
        nxt.sort(key=lambda b: -b[0])
        beams = nxt[:BEAM_WIDTH] or [(sc, end, picks + [None]) for sc, end, picks in beams]

    best = max(beams, key=lambda b: b[0])[2]
    return best + [None] * (len(ids) - len(best))


def _rows(h: Hollow, ids: list[int], filled: dict[int, str]) -> str:
    """One section's rows, with whatever is already written shown in place."""
    out = []
    for lid in ids:
        l = h.lines[lid]
        row = " ".join(("●" if s.stress else "○") + ("_" if s.held else "")
                       for s in l.slots)
        head = f"L{lid:02d} [{l.rhyme}] {len(l.slots):2d}  {row}"
        out.append(f"{head}   ALREADY WRITTEN: {filled[lid]}" if lid in filled
                   else f"{head}   <- write this one")
    return "\n".join(out)


_ANSWER = re.compile(r"^\s*L?(\d+)\s*[:.\)]\s*(.+?)\s*$", re.M)


def _missed(h: Hollow, lines: dict[int, str], ids: list[int]) -> list[str]:
    """The rows that came back wrong, and what is wrong with each."""
    out = []
    for lid in ids:
        if lid not in lines:
            continue
        want = len(h.lines[lid].slots)
        text = lines[lid]
        got = len(prosody.syllables_for(text, want))
        if got != want:
            out.append(f"L{lid:02d}: you wrote {text!r}, which is {got} written "
                       f"syllables. It needs exactly {want}.")
        elif (why := ragged(text)):
            out.append(f"L{lid:02d}: you wrote {text!r}. That is the right "
                       f"length, but {why}. Write a whole thought of exactly "
                       f"{want} syllables instead.")
    return out


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
    bar = stress_bar(licence)

    sections = h.sections or list(h.groups)
    echo = list(h.section_echo) + [None] * (len(sections) - len(h.section_echo))
    distinct = [i for i, e in enumerate(echo) if e is None]
    windows = _windows(c, [len(sections[i]) for i in distinct])

    lines: dict[int, str] = {}
    lifted: set[int] = set()  # this line is the corpus's own words
    used: set[int] = set()
    unanswered: list[str] = []

    share = rewrite_share(licence) if writer is not None else 0.0

    for k, si in enumerate(distinct):
        ids = sections[si]
        picks = _beam(c, h, ids, windows[k], used)
        fits: dict[int, Candidate] = {}
        gap: list[int] = []
        for lid, cand in zip(ids, picks):
            want = len(h.lines[lid].slots)
            if cand and cand.n == want and cand.stress_fit >= bar:
                fits[lid] = cand
            else:
                gap.append(lid)

        over = round(share * len(ids)) - len(gap)
        if over > 0:
            weakest = sorted(fits, key=lambda i: (fits[i].stress_fit, fits[i].score))
            for lid in weakest[:over]:
                del fits[lid]
                gap.append(lid)
        gap.sort()

        for lid, cand in fits.items():
            lines[lid] = cand.text
            lifted.add(lid)
            used.update(range(cand.i, cand.j))

        if gap and writer is not None and licence > QUOTE_END:
            before = lines.get(sections[distinct[k - 1]][-1]) if k else None
            prompt = PROMPT.format(
                legend=_rows(h, ids, {i: lines[i] for i in ids if i in lines}),
                corpus=c.phrase(*windows[k]),
                licence=licence, licence_note=_note(licence), n=len(gap),
            )
            if before:
                prompt += f"\nThe line before this section ends: {before!r}\n"
            try:
                reply = writer(prompt)
            except NeedsAnswer as need:
                unanswered.append(str(need))
                reply = ""
            for m in _ANSWER.finditer(reply):
                lid = int(m.group(1))
                if lid in gap:
                    lines[lid] = m.group(2).strip(' "')

            # The counting happens on this machine, so the model is never paid
            # to check its own arithmetic -- only to fix what really missed.
            missed = _missed(h, lines, gap)
            if missed:
                try:
                    reply = writer(prompt + REPAIR.format(rows="\n".join(missed)))
                except NeedsAnswer as need:
                    unanswered.append(str(need))
                    reply = ""
                for m in _ANSWER.finditer(reply):
                    lid = int(m.group(1))
                    if lid in gap:
                        lines[lid] = m.group(2).strip(' "')

        # Anything the writer did not fill takes the best phrase going.
        for lid, cand in zip(ids, picks):
            if lid not in lines and cand:
                lines[lid] = cand.text
                used.update(range(cand.i, cand.j))

    # A repeat is never searched for: it carries the words its first outing got.
    # This is the whole chorus rule, and it also puts repeats beyond the reach
    # of the reuse penalty and the positional bias, which used to drive the same
    # sung line to three different sets of words.
    for si, source in enumerate(echo):
        if source is None or len(sections[si]) != len(sections[source]):
            continue
        for here, there in zip(sections[si], sections[source]):
            if there in lines:
                lines[here] = lines[there]
                if there in lifted:
                    lifted.add(here)

    if unanswered:
        raise NeedsAnswer("\n".join(unanswered))

    log(f"licence {licence:.2f}: {len(lifted)}/{len(h.lines)} lines are the "
        f"corpus's own words")

    bends: list[Bend] = []
    for line in h.lines:
        want = len(line.slots)
        if line.id not in lines:
            lines[line.id] = "…"
            bends.append(Bend(line.id, want, 0, "the corpus has nothing this size"))
            continue
        lines[line.id] = _repair(lines[line.id], want)
        got = len(prosody.syllables_for(lines[line.id], want))
        if got != want:
            bends.append(Bend(line.id, want, got,
                              "nothing of this length could be found or written"))
        elif line.id not in lifted and writer is None and licence <= QUOTE_END:
            bends.append(Bend(line.id, want, got,
                              "nothing in the corpus fits this line's stresses"))

    section_of = [0] * len(h.lines)
    for si, ids in enumerate(sections):
        for lid in ids:
            if lid < len(section_of):
                section_of[lid] = si
    copies = {}
    for si, source in enumerate(echo):
        if source is not None and len(sections[si]) == len(sections[source]):
            copies.update(dict(zip(sections[si], sections[source])))

    return Dressing(
        licence=licence,
        corpus=corpus_name,
        lines=[lines[l.id] for l in h.lines],
        bends=bends,
        from_corpus=[l.id in lifted for l in h.lines],
        section=section_of,
        echo_of=[copies.get(l.id) for l in h.lines],
    )
