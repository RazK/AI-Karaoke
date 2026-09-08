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


def test_a_line_reads_the_same_whatever_it_is_measured_against():
    """A word has one reading here, not the reading that would flatter it.

    Letting a line be re-pronounced until it fitted made the exam generous to
    the point of uselessness: random text could be re-read into the right
    length. Words like "fire" do have more than one honest reading, and that
    cost is accepted in exchange for a score nothing can game.
    """
    for slots in (1, 2, 5, 9):
        assert prosody.syllables_for("fire in every hour", slots) == \
            prosody.syllables("fire in every hour")


def test_rhyme_labels_never_repeat():
    """Past Z the labels used to wrap, and told a writer to rhyme lines that
    had nothing in common."""
    lines = [f"a word ending in {w}" for w in
             "cat dog tree sun moon hill fork bell rain wolf ship gold lamp"
             " nest cup drum flag horn ice jug kite leaf mist nut oak pit"
             " quilt rope".split()]
    labels = prosody.rhyme_classes(lines)
    assert len(set(labels)) == len({prosody.rhyme_key(l) for l in lines})
