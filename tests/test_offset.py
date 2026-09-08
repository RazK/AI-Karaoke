"""Can the offset estimator find a lyric that is not where the file says?

The failure this stands in for is a song that opens with several seconds of
near-silence: the first line's timestamp is then no guide at all, and anything
that trusts it puts the whole lyric in the wrong place.

So: take a seeded song, prepend N seconds of digital silence to the recording,
separate and measure that, and hand the estimator the karaoke file it came with,
untouched. It has to say +N. The seeded songs come from JamendoLyrics, whose
timings were hand-checked against these very recordings, so the answer for N=0
is zero and the answer for N is N -- an absolute check, not just a differential.

Separation is the slow part. The stems are cached under .work/tests, so the
first run of this file takes a few minutes and later ones take seconds.
"""
from __future__ import annotations

import subprocess

import pytest

from conftest import LIBRARY, ROOT
from hollow import offset as offset_mod
from hollow.audio import analyse, duration as audio_duration, separate
from hollow.ingest import parse_lrc

WORK = ROOT / ".work" / "tests"
TOLERANCE_MS = 150
LEAD_INS = [0, 3, 7]


def _seed():
    """A library song that still has the karaoke file it was built from."""
    for song in LIBRARY.songs():
        lrc = ROOT / song.source_ref
        mix = LIBRARY.dir(song.ref) / "mix.mp3"
        if song.source_kind == "karaoke_file" and lrc.exists() and mix.exists():
            return song, mix, lrc
    pytest.skip("no seeded karaoke song in the library")


@pytest.fixture(scope="session")
def spans():
    _, _, lrc = _seed()
    words, _ = parse_lrc(lrc.read_text(encoding="utf-8"))
    return [(w.start, w.end) for w in words]


@pytest.fixture(scope="session")
def voicings():
    """One separated, measured vocal per lead-in length."""
    _, mix, _ = _seed()
    WORK.mkdir(parents=True, exist_ok=True)
    out = {}
    for n in LEAD_INS:
        shifted = WORK / f"lead{n}.wav"
        if not shifted.exists():
            pad = ["-af", f"adelay={n * 1000}|{n * 1000}"] if n else []
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mix)]
                + pad + [str(shifted)],
                check=True,
            )
        vocals, _ = separate(shifted, WORK / f"sep{n}")
        out[n] = (analyse(vocals), audio_duration(shifted))
    return out


@pytest.mark.parametrize("n", LEAD_INS)
def test_recovers_the_lead_in(spans, voicings, n):
    voicing, duration = voicings[n]
    got, confident = offset_mod.estimate(spans, voicing, duration)
    assert abs(got - n) * 1000 <= TOLERANCE_MS, f"wanted {n}s, got {got:+.3f}s"
    assert confident


def test_the_long_lead_in_is_really_silent(voicings):
    """Otherwise the hardest case is not being tested at all."""
    voicing, _ = voicings[max(LEAD_INS)]
    frames = int(max(LEAD_INS) / voicing.hop)
    assert voicing.activity()[:frames].mean() == 0.0
