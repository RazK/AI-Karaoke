"""HOLLOW — a song with its words hollowed out.

A HOLLOW file says how a song is sung and nothing about what it says. It
carries, for every syllable of the vocal: when it starts, how long it is held,
whether it is stressed, and where the melody sits relative to the start of its
line. It carries how lines group into phrases and which line endings rhyme with
which. It carries no words, no letters, no phonemes and no word boundaries, so
the original lyric cannot be read back out of it.

Song title and artist deliberately live in a separate library sidecar rather
than in the file: plenty of songs are named after one of their own lines.

That is the whole point of the format. Everything downstream -- the writer, the
exam, the player -- consumes HOLLOW, so nothing downstream ever sees a
copyrighted lyric.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

HOLLOW_VERSION = 1

# A slot voiced longer than this is a held note, and a held note wants a vowel
# that can actually be sustained.
HOLD_S = 0.6
# Below this, the aligner is telling us it does not know where the line is.
CONFIDENT = 0.5


@dataclass
class Slot:
    """One syllable-shaped hole in the song."""

    t: float  # onset, seconds into the audio
    sustain: float  # voiced length, NOT the gap to the next slot
    stress: bool
    pitch: int | None = None  # semitones relative to the line's first slot
    hold: bool = False  # the performance sustains an open vowel here

    @property
    def held(self) -> bool:
        return self.hold


@dataclass
class Line:
    id: int
    group: int
    slots: list[Slot]
    rhyme: str  # class label; lines sharing a label rhyme with each other
    confidence: float = 1.0
    # Absolute pitch of this line's first pitched slot. Slot.pitch is relative
    # to it, which is what a writer wants to read; this is what a synthesiser
    # needs so that line 2 sits where it should against line 1.
    ref_hz: float | None = None

    @property
    def start(self) -> float:
        return self.slots[0].t

    @property
    def end(self) -> float:
        return self.slots[-1].t + self.slots[-1].sustain

    @property
    def uncertain(self) -> bool:
        return self.confidence < CONFIDENT


@dataclass
class Hollow:
    song_ref: str  # content hash of the audio this was extracted from
    duration: float
    lines: list[Line]
    groups: list[list[int]]  # phrase groups, as lists of line ids
    rhyme_pairs: list[tuple[int, int]]
    source_kind: str  # "youtube" | "karaoke_file"
    offset_ms: int = 0  # correction applied to imported timings, for the record
    offset_confident: bool = True
    version: int = HOLLOW_VERSION
    notes: dict = field(default_factory=dict)

    # ── derived ────────────────────────────────────────────────────────────
    @property
    def n_slots(self) -> int:
        return sum(len(l.slots) for l in self.lines)

    def line(self, line_id: int) -> Line:
        return self.lines[line_id]

    # ── io ─────────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        d = asdict(self)
        d["rhyme_pairs"] = [list(p) for p in self.rhyme_pairs]
        return d

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1))
        return path

    @staticmethod
    def load(path: str | Path) -> "Hollow":
        return Hollow.from_dict(json.loads(Path(path).read_text()))

    @staticmethod
    def from_dict(d: dict) -> "Hollow":
        lines = [
            Line(
                id=l["id"],
                group=l["group"],
                rhyme=l["rhyme"],
                confidence=l.get("confidence", 1.0),
                ref_hz=l.get("ref_hz"),
                slots=[Slot(**s) for s in l["slots"]],
            )
            for l in d["lines"]
        ]
        return Hollow(
            song_ref=d["song_ref"],
            duration=d["duration"],
            lines=lines,
            groups=[list(g) for g in d["groups"]],
            rhyme_pairs=[tuple(p) for p in d["rhyme_pairs"]],
            source_kind=d["source_kind"],
            offset_ms=d.get("offset_ms", 0),
            offset_confident=d.get("offset_confident", True),
            version=d.get("version", HOLLOW_VERSION),
            notes=d.get("notes", {}),
        )


def pairs_from_classes(labels: list[str]) -> list[tuple[int, int]]:
    """Consecutive pairs within each rhyme class: A,B,A,B -> (0,2),(1,3)."""
    by_label: dict[str, list[int]] = {}
    for i, lab in enumerate(labels):
        by_label.setdefault(lab, []).append(i)
    out = []
    for ids in by_label.values():
        out.extend(zip(ids, ids[1:]))
    return sorted(out)


# ── the writer's view ──────────────────────────────────────────────────────

LEGEND = """\
LEGEND
  Each line is a row of slots. One slot takes exactly one written syllable.
    ●   this slot is stressed  -- put a stressed syllable on it
    ○   this slot is unstressed
    _   the slot before it is held long -- it needs an open vowel that can be
        sustained, not a schwa and not a syllable closed by t/d/k/p/b/g
    ?    at the start of a line: the timing here is uncertain, write it anyway
  [A]  lines sharing a letter must rhyme with each other at the line ending
  pitch  where the melody sits, in semitones from the first slot of that line
  Blank lines separate phrase groups. Write one line of words per row, in
  order, and never merge or split rows."""


def render(h: Hollow, groups: list[int] | None = None) -> str:
    """The word-free text handed to whoever is writing the new lyric.

    This is the only thing about a song that is ever sent to a language model.
    """
    want = set(groups) if groups is not None else set(range(len(h.groups)))
    out = [
        f"HOLLOW v{h.version} — {h.n_slots} slots over {len(h.lines)} lines, "
        f"{len(h.groups)} phrase groups.",
        "",
        LEGEND,
        "",
    ]
    for gi, line_ids in enumerate(h.groups):
        if gi not in want:
            continue
        out.append(f"GROUP {gi + 1}")
        for lid in line_ids:
            l = h.lines[lid]
            row = " ".join(
                ("●" if s.stress else "○") + ("_" if s.held else "")
                for s in l.slots
            )
            pitch = " ".join(
                "·" if s.pitch is None else f"{s.pitch:+d}" for s in l.slots
            )
            mark = "?" if l.uncertain else " "
            out.append(
                f" {mark}L{lid:02d} [{l.rhyme}] {len(l.slots):2d}  {row}"
                + (f"   pitch {pitch}" if any(s.pitch is not None for s in l.slots) else "")
            )
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def leaks(h: Hollow) -> list[str]:
    """Any free text in a HOLLOW file. Should always be empty.

    The format's central promise is that it holds no words, so we check rather
    than assert it: every string in the file has to be a fixed schema value.
    """
    allowed = {"youtube", "karaoke_file", "upload", "test", "file", "whisper"}
    bad = []

    def walk(v, path):
        if isinstance(v, str):
            ok = (
                v in allowed
                or (v.isalpha() and v.isupper())  # rhyme class label: A..Z, AA..
                or all(c in "0123456789abcdef" for c in v)  # content hash
            )
            if not ok:
                bad.append(f"{path}={v!r}")
        elif isinstance(v, dict):
            for k, sub in v.items():
                walk(sub, f"{path}.{k}")
        elif isinstance(v, (list, tuple)):
            for i, sub in enumerate(v):
                walk(sub, f"{path}[{i}]")

    walk(h.to_dict(), "")
    return bad
