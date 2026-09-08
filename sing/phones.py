"""CMU syllables -> espeak IPA, the phoneme alphabet piper speaks.

`hollow.prosody.syllables_for(text, n_slots)` hands us exactly one syllable per
slot, in ARPAbet. Piper's front end wants espeak-ng IPA. This module is the
bridge, and it is deliberately one-to-one: one written syllable in, one
pronounceable phoneme string out, so a slot never loses its syllable on the way
to the synthesiser.
"""
from __future__ import annotations

from dataclasses import dataclass

from hollow.prosody import Syl

# ARPAbet vowel -> espeak en-us IPA, keyed by the stress-stripped phone.
# AH is special: unstressed it is a schwa, stressed it is a wedge.
VOWELS = {
    "AA": "ɑː", "AE": "æ", "AH": "ʌ", "AO": "ɔː", "AW": "aʊ", "AY": "aɪ",
    "EH": "ɛ", "ER": "ɜː", "EY": "eɪ", "IH": "ɪ", "IY": "iː", "OW": "oʊ",
    "OY": "ɔɪ", "UH": "ʊ", "UW": "uː",
}
VOWELS_UNSTRESSED = {"AH": "ə", "ER": "ɚ", "IH": "ɪ", "UH": "ʊ"}

CONSONANTS = {
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p",
    "R": "ɹ", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}

STRESS = "ˈ"
# Vowel characters of the espeak inventory we emit, for finding the nucleus
# back in a phoneme string.
VOWEL_CHARS = set("aɐɑɒæeɛəɚɜiɪoɔʊuʌ")


@dataclass(frozen=True)
class Unit:
    """One slot's worth of sound: the phonemes, and where the vowel sits."""

    phonemes: tuple[str, ...]
    nucleus_from: int  # index of the first nucleus phoneme
    nucleus_to: int  # one past the last
    stressed: bool
    can_hold: bool

    @property
    def text(self) -> str:
        return "".join(self.phonemes)


def vowel(nucleus: str) -> str:
    """The IPA for one ARPAbet vowel phone, stress digit included."""
    base, digit = nucleus[:-1], nucleus[-1]
    if digit == "0" and base in VOWELS_UNSTRESSED:
        return VOWELS_UNSTRESSED[base]
    return VOWELS.get(base, VOWELS_UNSTRESSED.get(base, "ə"))


def unit(syl: Syl) -> Unit:
    """Turn one CMU syllable into a pronounceable espeak phoneme string."""
    # espeak's inventory is per character, so an affricate goes in as its two
    # letters; anything else and piper drops the phoneme on the floor.
    onset = [c for p in syl.onset if p in CONSONANTS for c in CONSONANTS[p]]
    coda = [c for p in syl.coda if p in CONSONANTS for c in CONSONANTS[p]]
    nuc = list(vowel(syl.nucleus))
    phones = list(onset)
    if syl.stressed:
        phones.append(STRESS)
    start = len(phones)
    phones += nuc
    end = len(phones)
    phones += coda
    return Unit(tuple(phones), start, end, syl.stressed, syl.can_hold)


def open_up(u: Unit) -> Unit:
    """A held slot wants a vowel that stays open.

    Held slots are marked in HOLLOW, and the exam already refuses words that
    close them with a stop, so this only has to lengthen the vowel rather than
    replace it: espeak's length mark on a short nucleus.
    """
    ph = list(u.phonemes)
    if u.nucleus_to - u.nucleus_from == 1 and ph[u.nucleus_from] in "æɛɪʊʌəɚ":
        ph.insert(u.nucleus_to, "ː")
        return Unit(tuple(ph), u.nucleus_from, u.nucleus_to + 1, u.stressed, u.can_hold)
    return u
