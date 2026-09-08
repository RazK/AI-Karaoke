"""When each written word is sung.

HOLLOW knows when every syllable slot opens. A written line's syllables map
onto those slots one for one, so a word starts at the slot its first syllable
lands on and ends where its last one stops. That is what the player highlights.
"""
from __future__ import annotations

from . import prosody
from .format import Hollow


def word_times(h: Hollow, lines: list[str]) -> list[list[dict]]:
    """Per line, the words with the times they are sung."""
    out = []
    for line, text in zip(h.lines, lines):
        n = len(line.slots)
        ws = prosody.words(text)
        counts = [len(prosody.pronunciations(w)[0]) for w in ws]
        # If the line does not fit, the syllables still have to go somewhere:
        # spread them over the slots we have rather than dropping words.
        total = sum(counts) or 1
        row, at = [], 0
        for w, c in zip(ws, counts):
            i = min(int(at * n / total), n - 1)
            j = min(int((at + c) * n / total), n) - 1
            j = max(j, i)
            start = line.slots[i].t
            end = line.slots[j].t + line.slots[j].sustain
            # `i` and `n` are which slots this word sits on. Both the original
            # and the rewrite land on the same slots, so a player that lays the
            # two out on one column-per-slot grid gets each new word directly
            # under the old word it replaces, for free.
            row.append({"w": w, "t": round(start, 3),
                        "d": round(max(end - start, 0.05), 3),
                        "i": i, "n": j - i + 1})
            at += c
        out.append(row)
    return out
