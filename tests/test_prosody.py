"""The three syllable questions the whole format rests on."""
from __future__ import annotations

from hollow import prosody


def test_queue_is_one_syllable():
    """Five letters, four of them vowels, one syllable. Letters are not slots."""
    assert len(prosody.pronunciations("queue")[0]) == 1


def test_cat_cannot_be_held():
    """A syllable closed by a stop is cut off by its own consonant."""
    (syl,) = prosody.pronunciations("cat")[0]
    assert not syl.can_hold


def test_open_syllable_can_be_held():
    (syl,) = prosody.pronunciations("day")[0]
    assert syl.can_hold


def test_fire_reads_as_the_slots_ask():
    """Some words have more than one honest reading, and a singer picks one."""
    assert len(prosody.syllables_for("fire", 1)) == 1
    assert len(prosody.syllables_for("fire", 2)) == 2


def test_reading_is_chosen_across_a_whole_line():
    """The choice is made for the line, not word by word."""
    line = "fire in every hour"
    assert len(prosody.syllables_for(line, 5)) == 5
    assert len(prosody.syllables_for(line, 7)) == 7
