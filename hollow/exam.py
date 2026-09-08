"""The singability exam.

Given a HOLLOW representation and a set of words placed on it, return a number
from 0 to 10.

    score = 8 * (mean over lines of fit) + 2 * form
    fit(line) = e^(-2.5 * |syllables written - slots in the line|)
    form = (1.0*stress + 0.5*rhyme + 0.5*vowel) / 2.0

An exact line scores 1, one syllable out scores 0.08, two out scores 0.007. A
cram is audible from the back of the room, so the curve is steep on purpose.

Lines the aligner could not place confidently are excluded and reported
separately. They are never silently counted as passes.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pronouncing

from . import prosody
from .format import Hollow


@dataclass
class LineScore:
    id: int
    slots: int
    written: int
    fit: float
    text: str


@dataclass
class Score:
    score: float
    fit: float
    stress: float
    rhyme: float
    vowel: float
    form: float
    lines: list[LineScore] = field(default_factory=list)
    excluded: list[int] = field(default_factory=list)
    held_slots: int = 0
    rhyme_pairs: int = 0

    def __str__(self) -> str:
        return (
            f"{self.score:5.2f}/10  fit {self.fit:.3f}  "
            f"stress {self.stress:.2f}  rhyme {self.rhyme:.2f} "
            f"({self.rhyme_pairs} pairs)  vowel {self.vowel:.2f} "
            f"({self.held_slots} held)  form {self.form:.3f}"
            + (f"  [{len(self.excluded)} lines excluded]" if self.excluded else "")
        )


def score(h: Hollow, written: list[str]) -> Score:
    """Score `written` -- one line of words per line of the representation."""
    if len(written) != len(h.lines):
        raise ValueError(
            f"{len(written)} written lines for {len(h.lines)} slots lines; "
            "one original line becomes one rewritten line"
        )

    scored, excluded = [], []
    fits: list[float] = []
    stress_hit = stress_total = 0
    vowel_hit = vowel_total = 0

    for line, text in zip(h.lines, written):
        if line.uncertain:
            excluded.append(line.id)
            continue
        scored.append(line.id)
        n = len(line.slots)
        syls = prosody.syllables_for(text, n)
        fit = math.exp(-2.5 * abs(len(syls) - n))
        fits.append(fit)

        # Stress and vowel are credited in proportion to how well the line
        # fits. If the syllable count is wrong the words are not on these slots
        # at all, so agreeing with one by accident earns almost nothing. This
        # is what keeps a line of the right shape apart from a line that merely
        # happens to put a stress in the right place.
        stress_total += max(n, len(syls))
        for i in range(min(n, len(syls))):
            if syls[i].stressed == line.slots[i].stress:
                stress_hit += fit

        for i, slot in enumerate(line.slots):
            if not slot.held:
                continue
            vowel_total += 1
            if i < len(syls) and syls[i].can_hold:
                vowel_hit += fit

    ok = set(scored)
    by_id = dict(zip(scored, fits))
    pairs = [(a, b) for a, b in h.rhyme_pairs if a in ok and b in ok]
    rhyme_hit = sum(
        min(by_id[a], by_id[b]) for a, b in pairs if prosody.rhymes(written[a], written[b])
    )

    mean_fit = sum(fits) / len(fits) if fits else 0.0
    stress = stress_hit / stress_total if stress_total else 1.0
    rhyme = rhyme_hit / len(pairs) if pairs else 1.0
    vowel = vowel_hit / vowel_total if vowel_total else 1.0
    form = (1.0 * stress + 0.5 * rhyme + 0.5 * vowel) / 2.0

    return Score(
        score=8 * mean_fit + 2 * form,
        fit=mean_fit,
        stress=stress,
        rhyme=rhyme,
        vowel=vowel,
        form=form,
        excluded=excluded,
        held_slots=vowel_total,
        rhyme_pairs=len(pairs),
        lines=[
            LineScore(l.id, len(l.slots), len(prosody.syllables_for(t, len(l.slots))),
                      math.exp(-2.5 * abs(len(prosody.syllables_for(t, len(l.slots))) - len(l.slots))), t)
            for l, t in zip(h.lines, written)
            if not l.uncertain
        ],
    )


# ── the four calibration cases ─────────────────────────────────────────────
#
# These are the acceptance test for the format, not for the scorer. Cases 1 and
# 2 differ only in stress, rhyme and vowel quality -- the timing is identical.
# If the representation did not record those things the two would score the
# same, and the exam would be blind to the difference between the real lyric
# and any arbitrary text with the right syllable counts.

_BY_SYLLABLES: dict[int, list[str]] = {}


def _pool() -> dict[int, list[str]]:
    """Ordinary words grouped by syllable count, for building fake lyrics."""
    if not _BY_SYLLABLES:
        for word, phones in pronouncing.cmudict.entries():
            if not word.isalpha() or len(word) < 3:
                continue
            n = sum(p[-1].isdigit() for p in phones)
            if 1 <= n <= 4:
                _BY_SYLLABLES.setdefault(n, []).append(word)
    return _BY_SYLLABLES


def case_same_counts(h: Hollow, rng: random.Random) -> list[str]:
    """Every word replaced by a different word of the same syllable count."""
    pool = _pool()
    out = []
    for line in h.lines:
        need, got = len(line.slots), []
        while need > 0:
            n = min(need, rng.choice([1, 1, 2, 3]))
            got.append(rng.choice(pool[n]))
            need -= n
        out.append(" ".join(got))
    return out


def case_random_counts(h: Hollow, rng: random.Random) -> list[str]:
    """Words of random syllable count, so lines run long and short at random."""
    pool = _pool()
    out = []
    for line in h.lines:
        n = len(line.slots)
        # A random count is a wrong count: at least two syllables out, either
        # way, so lines run long and short at random.
        target = n + rng.choice([-4, -3, -2, 2, 3, 4, 5])
        if target < 1:
            target = n + rng.choice([2, 3, 4, 5])
        got, have = [], 0
        while have < target:
            k = rng.choice([1, 2, 3, 4])
            got.append(rng.choice(pool[k]))
            have += k
        out.append(" ".join(got))
    return out


def case_one_too_many(original: list[str]) -> list[str]:
    """Every other line given one syllable too many, the rest left correct.

    The extra syllable goes inside the line, so the line ending -- and with it
    the rhyme -- survives, and only the timing and stress go wrong.
    """
    out = []
    for i, text in enumerate(original):
        if i % 2 == 0:
            out.append(text)
            continue
        ws = text.split()
        at = 1 if len(ws) > 1 else 0
        out.append(" ".join(ws[:at] + ["and"] + ws[at:]))
    return out


@dataclass
class Calibration:
    original: Score
    same_counts: Score
    random_counts: Score
    one_too_many: Score

    def failures(self) -> list[str]:
        """Empty when the exam is calibrated. Checked on every build."""
        bad = []
        if not 9.995 <= self.original.score <= 10.0001:
            bad.append(f"original scored {self.original.score:.3f}, must be 10")
        if self.same_counts.score < 8.0:
            bad.append(f"same-syllable-count scored {self.same_counts.score:.3f}, must be >= 8")
        if self.random_counts.score >= 1.0:
            bad.append(f"random-count scored {self.random_counts.score:.3f}, must be ~0")
        if not 5.0 <= self.one_too_many.score <= 6.5:
            bad.append(f"one-too-many scored {self.one_too_many.score:.3f}, must be 5-6")
        gap = self.original.score - self.same_counts.score
        if gap < 0.5:
            bad.append(
                f"original and same-syllable-count differ by only {gap:.3f}: the "
                "representation is not recording stress, rhyme or vowel"
            )
        return bad

    def __str__(self) -> str:
        return "\n".join(
            [
                f"  1 original words          {self.original}",
                f"  2 same syllable counts    {self.same_counts}",
                f"  3 random syllable counts  {self.random_counts}",
                f"  4 every other line +1     {self.one_too_many}",
            ]
        )


def calibrate(h: Hollow, original: list[str], seed: int = 0) -> Calibration:
    """Run the four cases against one song. `original` never leaves the machine."""
    rng = random.Random(seed)
    return Calibration(
        original=score(h, original),
        same_counts=score(h, case_same_counts(h, rng)),
        random_counts=score(h, case_random_counts(h, rng)),
        one_too_many=score(h, case_one_too_many(original)),
    )
