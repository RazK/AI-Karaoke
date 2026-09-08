#!/usr/bin/env python3
"""Seed the library from a YouTube URL.

There is no karaoke file on this path. The words and their timings are read off
the recording's own separated vocal by a whisper running on this machine, so the
offset is zero by construction and no lyric ever leaves the box. This is the
path a stranger's song takes, and it is the one a dense modern pop mix has to
survive.

    tools/youtube.py <url> [title] [artist]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollow.exam import calibrate
from hollow.ingest import fetch_youtube, ingest
from hollow.library import Library

# Under .work/ with the stems: it is a copy of somebody's recording, and the
# repository deliberately keeps none of those.
DOWNLOADS = Path(".work") / "downloads"


def seed(url: str, title: str = "", artist: str = "", lib: Library | None = None,
         log=print) -> str:
    lib = lib or Library()
    mp3, meta = fetch_youtube(url, DOWNLOADS, log=log)
    h, originals, instrumental, mix = ingest(
        mp3, source_kind="youtube", work_dir=Path(".work") / meta["id"], log=log,
    )
    lib.add(h, originals, title=title or meta["title"],
            artist=artist or meta["artist"],
            instrumental=instrumental, mix=mix, source_ref=meta["url"])
    log(f"added {title or meta['title']} — {artist or meta['artist']}  "
        f"ref={h.song_ref}")
    # The calibration is the only check that says whether the representation is
    # any good, and on this path there is no hand-checked timing to fall back
    # on, so print it while the originals are still in hand.
    log(str(calibrate(h, originals)))
    return h.song_ref


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    seed(*sys.argv[1:4])
