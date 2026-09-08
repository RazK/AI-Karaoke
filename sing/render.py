"""Sing a line of words onto a line of HOLLOW.

Nothing in here listens to the original recording. The input is the
representation -- slot onsets, sustains, stresses, holds and semitones, plus
the line's ref_hz -- and a string of words. The output is a voice.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hollow import prosody
from hollow.format import Hollow, Line

from . import melody, world
from .phones import Unit, open_up, unit
from .voice import Voice


@dataclass
class Note:
    """One sound to make: a syllable, a moment, a length and a frequency."""

    t: float
    dur: float
    hz: float
    u: Unit
    stress: bool
    hold: bool
    melisma: bool  # a re-articulated vowel, not a new syllable


@dataclass
class LinePlan:
    line: int
    notes: list[Note]
    slots: int
    written: int


MIN_NOTE = 0.11
MAX_NOTE = 4.5


def plan_line(line: Line, text: str, ref_hz: float, octaves: int = 0) -> LinePlan:
    """Lay the syllables of `text` over the slots of `line`.

    One syllable per slot is the contract, and the exam is what enforces it.
    When a line does not honour it the singer still has to sing something, so a
    short line spills its last vowel onto the spare notes and a long line
    crams; both are what a person does, and both are audible.
    """
    n = len(line.slots)
    syls = prosody.syllables_for(text, n)
    hz = melody.line_hz(line, ref_hz, octaves=octaves)
    notes: list[Note] = []
    if not syls:
        return LinePlan(line.id, notes, n, 0)

    # slot index for each written syllable, spread evenly over the line
    owner = [min(n - 1, j * n // len(syls)) for j in range(len(syls))]
    per_slot: list[list[int]] = [[] for _ in range(n)]
    for j, s in enumerate(owner):
        per_slot[s].append(j)

    last: Unit | None = None
    for i, slot in enumerate(line.slots):
        dur = float(np.clip(slot.sustain, MIN_NOTE, MAX_NOTE))
        js = per_slot[i]
        if not js:
            # a spare note: hold the vowel we are already on
            if last is None:
                continue
            notes.append(Note(slot.t, dur, hz[i], _vowel_only(last), slot.stress,
                              slot.hold, True))
            continue
        share = dur / len(js)
        for k, j in enumerate(js):
            u = unit(syls[j])
            if slot.hold and len(js) == 1:
                u = open_up(u)
            last = u
            notes.append(Note(slot.t + k * share, share, hz[i], u, slot.stress,
                              slot.hold and len(js) == 1, False))
    return LinePlan(line.id, notes, n, len(syls))


def _vowel_only(u: Unit) -> Unit:
    ph = u.phonemes[u.nucleus_from :]
    return Unit(ph, 0, u.nucleus_to - u.nucleus_from, u.stressed, u.can_hold)


def sing_note(voice: Voice, note: Note, prev_hz: float | None, seed: int) -> np.ndarray:
    """One syllable, spoken by the TTS and rebuilt as a sung note."""
    a, ns, ne = voice.say(note.u)
    sr = voice.sr
    f0, sp, ap = world.analyse(a, sr)
    if len(f0) < 3:
        return np.zeros(int(note.dur * sr))
    i0 = int(ns / sr * 1000.0 / world.FP)
    i1 = max(i0 + 1, int(ne / sr * 1000.0 / world.FP))
    m = max(2, int(round(note.dur * 1000.0 / world.FP)))
    idx = world.time_map(len(f0), i0, i1, m)
    hz = melody.contour(note.hz, note.dur, world.FP, from_hz=prev_hz, seed=seed)
    out = world.resynth(f0, sp, ap, idx, hz, sr, core=(i0, i1))
    if out.size == 0:
        return np.zeros(int(note.dur * sr))
    rel = 0.05 if note.dur < 0.5 else 0.10
    out = out * melody.envelope(out.size, sr, release=min(rel, note.dur * 0.3))
    rms = float(np.sqrt((out**2).mean()) + 1e-9)
    gain = (0.10 / rms) * (1.18 if note.stress else 1.0)
    return out * min(gain, 6.0)


def sing(
    h: Hollow,
    lines: list[str],
    refs: dict[int, float],
    voice: Voice,
    *,
    default_hz: float = melody.COMFORT,
    log=print,
) -> tuple[np.ndarray, list[LinePlan]]:
    """Render every line. Returns the vocal track and what was actually sung."""
    sr = voice.sr
    buf = np.zeros(int((h.duration + 6.0) * sr))
    octaves = melody.song_octaves(h.lines, refs)
    if octaves:
        log(f"transposing the whole song by {octaves:+d} octave(s) to sing it")
    plans: list[LinePlan] = []
    for line, text in zip(h.lines, lines):
        ref = refs.get(line.id, default_hz)
        plan = plan_line(line, text, ref, octaves)
        plans.append(plan)
        prev_hz = None
        prev_end = -1.0
        for k, note in enumerate(plan.notes):
            slur = prev_hz if (prev_end >= 0 and note.t - prev_end < 0.12) else None
            y = sing_note(voice, note, slur, seed=line.id * 997 + k)
            i = int(round(note.t * sr))
            j = min(len(buf), i + y.size)
            if j > i:
                buf[i:j] += y[: j - i]
            prev_hz, prev_end = note.hz, note.t + note.dur
    return buf, plans
