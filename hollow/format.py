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
import re
from dataclasses import asdict, dataclass, field

from .prosody import _label as prosody_label
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
    # Which repeat class this line belongs to, or None if it is sung once.
    # Lines sharing a label are the SAME line of the song -- the chorus -- and
    # must carry the same rewritten words wherever they appear.
    echo: str | None = None

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
    # Sections are what a singer would call verse, chorus, bridge: an ordered
    # partition of every line. `groups` are breath groups from silence gaps and
    # can run twenty lines long, which is no use for writing a song a part at a
    # time. `section_echo[i]` is the earlier section that section i repeats.
    sections: list[list[int]] = field(default_factory=list)
    section_echo: list[int | None] = field(default_factory=list)
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
                echo=l.get("echo"),
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
            # A file written before sections existed falls back to its breath
            # groups, so every song already in the library still loads.
            sections=[list(g) for g in d.get("sections") or d["groups"]],
            section_echo=list(d.get("section_echo") or []),
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


# ── sections and repeats ───────────────────────────────────────────────────

MAX_SECTION_LINES = 10
# Below this a section is a stub, not a part of a song.
MIN_SECTION_LINES = 3
# What a section may grow to by swallowing a stub beside it.
MERGE_CAP = MAX_SECTION_LINES + MIN_SECTION_LINES
REFRAIN_MAX = 12
SAME_LINE_OVERLAP = 0.8


def _norm(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9']+", text.lower()))


def echo_labels(texts: list[str], shapes: list[tuple]) -> list[str | None]:
    """Label the lines that are the same line of the song sung again.

    Two lines are the same line if their words match -- but a transcriber does
    not render a repeated chorus identically every time, so near-matches count
    too, and only when the song's own shape agrees. That shape, the slot count
    and stress pattern, matched every true repeat across five songs and never
    missed one, so demanding it costs nothing and throws out the near-matches
    that merely sound alike.
    """
    norm = [_norm(t) for t in texts]
    classes: list[list[int]] = []
    for i, words in enumerate(norm):
        if not words:
            continue
        for members in classes:
            j = members[0]
            if shapes[i] != shapes[j]:
                continue
            a, b = set(words), set(norm[j])
            if norm[i] == norm[j] or len(a & b) / max(len(a | b), 1) >= SAME_LINE_OVERLAP:
                members.append(i)
                break
        else:
            classes.append([i])

    labels: list[str | None] = [None] * len(texts)
    n = 0
    for members in sorted((m for m in classes if len(m) > 1), key=lambda m: m[0]):
        label = prosody_label(n)
        n += 1
        for i in members:
            labels[i] = label
    return labels


def find_refrain(labels: list[str | None]) -> tuple[int, list[int]] | None:
    """The longest run of lines that comes back later, unchanged.

    That run is the chorus. Returns its length and where each occurrence starts.
    """
    n = len(labels)
    for length in range(min(REFRAIN_MAX, n), 0, -1):
        seen: dict[tuple, list[int]] = {}
        for i in range(n - length + 1):
            key = tuple(labels[i : i + length])
            if None in key:
                continue
            seen.setdefault(key, []).append(i)
        for starts in seen.values():
            spread = []
            for s in starts:
                if not spread or s >= spread[-1] + length:
                    spread.append(s)
            if len(spread) >= 2:
                return length, spread
    return None


def _merge_stubs(sections: list[list[int]], echo: list[int | None],
                 refrain: set[int]) -> tuple[list[list[int]], list[int | None]]:
    """Fold one- and two-line leftovers into the part beside them.

    A transcript leaves stubs -- a single line stranded between two choruses,
    or a two-line tail. A stub is the worst thing to hand a writer: one line,
    no context, and nothing around it to read against. It is also a section
    boundary the song does not actually have. Choruses are never touched: their
    boundaries are real and their words are copied between them.
    """
    rec = [{"ids": list(ids), "echo": None, "refrain": k in refrain}
           for k, ids in enumerate(sections)]
    for k, source in enumerate(echo):
        if source is not None:
            rec[k]["echo"] = rec[source]

    merged = True
    while merged:
        merged = False
        for k, r in enumerate(rec):
            if r["refrain"] or len(r["ids"]) >= MIN_SECTION_LINES:
                continue
            for j in (k - 1, k + 1):
                if not 0 <= j < len(rec) or rec[j]["refrain"]:
                    continue
                # A stub is one or two lines; a part of eleven is still short
                # enough to hold in view, and much better than a part of one.
                if len(rec[j]["ids"]) + len(r["ids"]) > MERGE_CAP:
                    continue
                rec[j]["ids"] = sorted(rec[j]["ids"] + r["ids"])
                del rec[k]
                merged = True
                break
            if merged:
                break

    where = {id(r): k for k, r in enumerate(rec)}
    return ([r["ids"] for r in rec],
            [where[id(r["echo"])] if r["echo"] is not None else None for r in rec])


def sections_from(labels: list[str | None], groups: list[list[int]],
                  n_lines: int) -> tuple[list[list[int]], list[int | None]]:
    """Cut the song into verses and choruses.

    The refrain's occurrences become sections that point at the first one, so
    the engine writes those words once. Everything else is split at the
    refrain's edges and at the breath groups, and capped short enough that a
    writer can hold a whole section in view at once.
    """
    refrain = find_refrain(labels)
    claimed: dict[int, int] = {}  # line id -> occurrence index
    if refrain:
        length, starts = refrain
        for k, s in enumerate(starts):
            for i in range(s, s + length):
                claimed[i] = k

    breaks = {g[0] for g in groups}
    sections: list[list[int]] = []
    echo: list[int | None] = []
    refrain_at: set[int] = set()
    first_refrain: int | None = None

    i = 0
    while i < n_lines:
        if i in claimed:
            length = refrain[0]
            sections.append(list(range(i, i + length)))
            echo.append(None if first_refrain is None else first_refrain)
            refrain_at.add(len(sections) - 1)
            if first_refrain is None:
                first_refrain = len(sections) - 1
            i += length
            continue
        run = []
        while i < n_lines and i not in claimed:
            if run and (i in breaks or len(run) >= MAX_SECTION_LINES):
                break
            run.append(i)
            i += 1
        sections.append(run)
        echo.append(None)
    return _merge_stubs(sections, echo, refrain_at)
