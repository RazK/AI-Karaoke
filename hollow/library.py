"""Where songs live on disk.

    library/songs.json                  title, artist, where it came from
    library/<ref>/hollow.json           the representation — word-free
    library/<ref>/originals.txt         the original lyric — never leaves here
    library/<ref>/instrumental.mp3      this recording's own backing track
    library/<ref>/mix.mp3               this recording
    library/<ref>/dressed/<id>.json     a rewrite, its score and its bends

`ref` is a hash of the audio, not a slug of the title, so that nothing in the
representation's own filename gives the song's words away.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .format import Hollow

ROOT = Path("library")


@dataclass
class Song:
    ref: str
    title: str
    artist: str
    source_kind: str
    source_ref: str = ""
    n_lines: int = 0
    duration: float = 0.0
    uncertain_lines: int = 0
    offset_ms: int = 0
    offset_confident: bool = True
    notes: dict = field(default_factory=dict)


class Library:
    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root)
        self.index = self.root / "songs.json"

    # ── index ──────────────────────────────────────────────────────────────
    def songs(self) -> list[Song]:
        if not self.index.exists():
            return []
        return [Song(**s) for s in json.loads(self.index.read_text())]

    def get(self, ref: str) -> Song | None:
        return next((s for s in self.songs() if s.ref == ref), None)

    def _write(self, songs: list[Song]) -> None:
        self.index.parent.mkdir(parents=True, exist_ok=True)
        self.index.write_text(json.dumps([s.__dict__ for s in songs], indent=1))

    # ── paths ──────────────────────────────────────────────────────────────
    def dir(self, ref: str) -> Path:
        return self.root / ref

    def hollow(self, ref: str) -> Hollow:
        return Hollow.load(self.dir(ref) / "hollow.json")

    def originals(self, ref: str) -> list[str]:
        """The song's own words. Used by the exam. Never sent anywhere."""
        p = self.dir(ref) / "originals.txt"
        return p.read_text(encoding="utf-8").splitlines() if p.exists() else []

    def dressed_dir(self, ref: str) -> Path:
        return self.dir(ref) / "dressed"

    def dressings(self, ref: str) -> list[dict]:
        d = self.dressed_dir(ref)
        return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.is_dir() else []

    # ── writing ────────────────────────────────────────────────────────────
    def add(
        self,
        h: Hollow,
        originals: list[str],
        *,
        title: str,
        artist: str,
        instrumental: Path,
        mix: Path,
        source_ref: str = "",
    ) -> Song:
        import shutil

        from .audio import to_mp3

        d = self.dir(h.song_ref)
        d.mkdir(parents=True, exist_ok=True)
        h.save(d / "hollow.json")
        (d / "originals.txt").write_text("\n".join(originals) + "\n", encoding="utf-8")
        to_mp3(instrumental, d / "instrumental.mp3")
        if Path(mix).suffix.lower() == ".mp3":
            shutil.copyfile(mix, d / "mix.mp3")
        else:
            to_mp3(mix, d / "mix.mp3")

        song = Song(
            ref=h.song_ref, title=title, artist=artist,
            source_kind=h.source_kind, source_ref=source_ref,
            n_lines=len(h.lines), duration=h.duration,
            uncertain_lines=sum(l.uncertain for l in h.lines),
            offset_ms=h.offset_ms, offset_confident=h.offset_confident,
            notes=h.notes,
        )
        songs = [s for s in self.songs() if s.ref != song.ref] + [song]
        self._write(songs)
        return song

    def save_dressing(self, ref: str, name: str, payload: dict) -> Path:
        d = self.dressed_dir(ref)
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{name}.json"
        p.write_text(json.dumps(payload, indent=1))
        return p

    # ── human ratings ──────────────────────────────────────────────────────
    def ratings_path(self) -> Path:
        return self.root / "ratings.json"

    def ratings(self) -> list[dict]:
        p = self.ratings_path()
        return json.loads(p.read_text()) if p.exists() else []

    def rate(self, ref: str, dressing: str, stars: float, machine: float) -> dict:
        row = {"ref": ref, "dressing": dressing, "human": stars, "machine": machine,
               "gap": round(abs(stars - machine), 2)}
        rows = [r for r in self.ratings() if not (r["ref"] == ref and r["dressing"] == dressing)]
        rows.append(row)
        self.ratings_path().parent.mkdir(parents=True, exist_ok=True)
        self.ratings_path().write_text(json.dumps(rows, indent=1))
        return row

    def disagreements(self, threshold: float = 2.0) -> list[dict]:
        """Songs where the human and the exam disagree by more than two points.

        A disagreement means the exam is measuring the wrong thing. The weights
        are a starting point, not a settled answer -- so these are shown, and
        nothing is refitted automatically.
        """
        return sorted((r for r in self.ratings() if r["gap"] > threshold),
                      key=lambda r: -r["gap"])
