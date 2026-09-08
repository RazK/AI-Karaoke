#!/usr/bin/env python3
"""Seed the library from JamendoLyrics — freely licensed songs that come with
hand-checked word timings.

They are the known-good material: the player is proved against them first, and
the exam's calibration runs over them on every build. The pipeline treats them
like any other karaoke file, so this path is not a special case.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.extract import TimedWord
from hollow.ingest import ingest, to_lrc
from hollow.library import Library
from hollow import prosody

REPO = "jamendolyrics/jamendolyrics"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main"
KARAOKE = Path("karaoke")


def _hf(path: str) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(REPO, path, repo_type="dataset"))


def english_songs() -> list[dict]:
    with open(_hf("JamendoLyrics.csv")) as f:
        return [r for r in csv.DictReader(f) if r["Language"] == "English"]


def timed_words(song_id: str) -> list[TimedWord]:
    """Zip the line texts against the word timing table."""
    with open(_hf(f"annotations/lines/{song_id}.csv")) as f:
        lines = [r for r in csv.DictReader(f) if r["lyrics_line"].strip()]
    with open(_hf(f"annotations/words/{song_id}.csv")) as f:
        stamps = list(csv.DictReader(f))

    out, k = [], 0
    for i, row in enumerate(lines):
        for w in prosody.words(row["lyrics_line"]):
            if k >= len(stamps):
                break
            s = stamps[k]
            out.append(TimedWord(w, float(s["word_start"]), float(s["word_end"]), i))
            k += 1
    return out


def download_mp3(song_id: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    for url in (f"{BASE}/subsets/en/mp3/{song_id}.mp3", f"{BASE}/mp3/{song_id}.mp3"):
        r = requests.get(url, timeout=120)
        if r.ok and len(r.content) > 10_000:
            dest.write_bytes(r.content)
            return dest
    raise RuntimeError(f"could not fetch audio for {song_id}")


def seed(song_id: str, title: str, artist: str, lib: Library, log=print) -> str:
    """Write the karaoke file, then import it exactly like any other."""
    KARAOKE.mkdir(parents=True, exist_ok=True)
    lrc_path = KARAOKE / f"{song_id}.lrc"
    if not lrc_path.exists():
        lrc_path.write_text(to_lrc(timed_words(song_id), {"ti": title, "ar": artist}),
                            encoding="utf-8")
        log(f"wrote {lrc_path}")
    mp3 = download_mp3(song_id, KARAOKE / f"{song_id}.mp3")

    h, originals, instrumental, mix = ingest(
        mp3, lrc=lrc_path.read_text(encoding="utf-8"),
        source_kind="karaoke_file", work_dir=Path(".work") / song_id, log=log,
    )
    lib.add(h, originals, title=title, artist=artist,
            instrumental=instrumental, mix=mix, source_ref=str(lrc_path))
    log(f"added {title} — {artist}  ref={h.song_ref}")
    return h.song_ref


if __name__ == "__main__":
    lib = Library()
    if len(sys.argv) < 2:
        for r in english_songs():
            marks = " ".join(k for k in ("NonLexical", "Polyphonic") if r[k] == "true")
            print(f"{Path(r['Filepath']).stem:45} {r['Artist']} — {r['Title']} "
                  f"({r['Genre']}) {marks}")
        raise SystemExit(0)
    for sid in sys.argv[1:]:
        row = next(r for r in english_songs() if Path(r["Filepath"]).stem == sid)
        seed(sid, row["Title"], row["Artist"], lib)
