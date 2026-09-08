"""Syllable-level prosody, from the CMU pronouncing dictionary.

Everything the rest of the system needs to know about how a written word is
sung: how many syllables it has, which of them carry stress, whether a
syllable can be held on a long note, and what rhymes with what.

Nothing here touches audio and nothing here calls a network.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass

import pronouncing

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")

# CMU marks vowels with a trailing stress digit; consonants have none.
_STOPS = frozenset({"P", "B", "T", "D", "K", "G", "CH", "JH"})
_SCHWA = "AH0"


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


@dataclass(frozen=True)
class Syl:
    """One syllable: what a single slot in a song has to be filled with."""

    onset: tuple[str, ...]
    nucleus: str  # vowel phone including its stress digit, e.g. "AE1"
    coda: tuple[str, ...]

    @property
    def stressed(self) -> bool:
        return self.nucleus[-1] in "12"

    @property
    def can_hold(self) -> bool:
        """True if this syllable can be sustained on a long note.

        A schwa has no body to hold and a syllable closed by a stop is cut
        off by its own consonant. Everything else can be held open.
        """
        return self.nucleus != _SCHWA and not (set(self.coda) & _STOPS)


def _syllabify(phones: list[str]) -> list[Syl]:
    """Split a CMU phone string into syllables.

    Consonants between two vowels are split by the one-consonant onset rule:
    the last consonant of the run starts the next syllable, the rest close the
    previous one. That is enough to answer the only two questions we ask of a
    syllable -- is its nucleus a schwa, and is it closed by a stop.
    """
    nuclei = [i for i, p in enumerate(phones) if p[-1].isdigit()]
    if not nuclei:
        return []
    out: list[Syl] = []
    for k, n in enumerate(nuclei):
        prev = nuclei[k - 1] if k else -1
        nxt = nuclei[k + 1] if k + 1 < len(nuclei) else len(phones)
        run_before = phones[prev + 1 : n]
        run_after = phones[n + 1 : nxt]
        onset = tuple(run_before) if k == 0 else tuple(run_before[-1:])
        coda = tuple(run_after) if k == len(nuclei) - 1 else tuple(run_after[:-1])
        out.append(Syl(onset, phones[n], coda))
    return out


def _guess(word: str) -> list[Syl]:
    """Fallback for words the dictionary does not have.

    Counts vowel groups, alternates stress from the first syllable, and lets a
    syllable be held unless it ends in a stop letter.
    """
    w = word.lower()
    groups = re.findall(r"[aeiouy]+", w)
    if w.endswith("e") and len(groups) > 1 and not w.endswith(("le", "ee", "ye")):
        groups.pop()
    n = max(1, len(groups))
    out = []
    for i in range(n):
        last = i == n - 1
        coda = ("T",) if last and w[-1] in "pbtdkgc" else ()
        out.append(Syl((), "AA1" if i % 2 == 0 else "AH0", coda))
    return out


@functools.lru_cache(maxsize=100_000)
def pronunciations(word: str) -> tuple[tuple[Syl, ...], ...]:
    """Every dictionary reading of a word, as syllables. Never empty."""
    clean = word.lower().strip("'’-")
    variants = [_syllabify(p.split()) for p in pronouncing.phones_for_word(clean)]
    variants = [v for v in variants if v]
    if not variants:
        variants = [_guess(clean)]
    seen, uniq = set(), []
    for v in variants:
        key = tuple(v)
        if key not in seen:
            seen.add(key)
            uniq.append(tuple(v))
    return tuple(uniq)


def syllables(text: str) -> list[Syl]:
    """Syllables of a line, using each word's first dictionary reading."""
    return [s for w in words(text) for s in pronunciations(w)[0]]


def count(text: str) -> int:
    return len(syllables(text))


def syllables_for(text: str, n_slots: int) -> list[Syl]:
    """Syllables of a line, read the way a singer with `n_slots` would read it.

    Words like "fire" and "every" have more than one honest reading. This picks
    the combination of readings whose total lands closest to the slots on
    offer, then falls back to the first reading of each word.
    """
    ws = words(text)
    if not ws:
        return []
    # best[total] = list of chosen readings reaching that total
    best: dict[int, list[tuple[Syl, ...]]] = {0: []}
    for w in ws:
        nxt: dict[int, list[tuple[Syl, ...]]] = {}
        for total, chosen in best.items():
            for reading in pronunciations(w):
                t = total + len(reading)
                if t not in nxt:
                    nxt[t] = chosen + [reading]
        best = nxt
        if len(best) > 64:  # keep the search near the target on long lines
            keep = sorted(best, key=lambda t: abs(t - n_slots))[:64]
            best = {t: best[t] for t in keep}
    total = min(best, key=lambda t: (abs(t - n_slots), t))
    return [s for reading in best[total] for s in reading]


def stresses(text: str) -> list[bool]:
    return [s.stressed for s in syllables(text)]


# ── rhyme ──────────────────────────────────────────────────────────────────

def rhyme_key(text: str) -> str:
    """A key such that two lines rhyme iff their keys are equal."""
    ws = words(text)
    if not ws:
        return ""
    last = ws[-1].lower().strip("'’-")
    phones = pronouncing.phones_for_word(last)
    if phones:
        return pronouncing.rhyming_part(phones[0])
    return last[-3:]


def rhyme_classes(lines: list[str]) -> list[str]:
    """Label lines A, B, C... so that lines sharing a label rhyme."""
    labels, seen = [], {}
    for line in lines:
        key = rhyme_key(line)
        if key not in seen:
            seen[key] = chr(ord("A") + len(seen) % 26)
        labels.append(seen[key])
    return labels


def rhymes(a: str, b: str) -> bool:
    ka, kb = rhyme_key(a), rhyme_key(b)
    return bool(ka) and ka == kb
