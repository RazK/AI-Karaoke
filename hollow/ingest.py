"""The two ways a song gets in.

A karaoke file with the recording it belongs to, or a YouTube URL. Both end at
the same HOLLOW file and the player cannot tell which one it got.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import offset as offset_mod
from . import prosody
from .audio import analyse, separate, sha256, duration as audio_duration
from .extract import TimedWord, build
from .format import Hollow

# ── karaoke files (LRC, plain and word-level) ──────────────────────────────

_TAG = re.compile(r"\[(\d+):(\d+(?:[.:]\d+)?)\]")
_WORD_TAG = re.compile(r"<(\d+):(\d+(?:[.:]\d+)?)>")
_META = re.compile(r"\[(ti|ar|al|by|offset):([^\]]*)\]", re.I)


def _stamp(m: re.Match) -> float:
    return int(m.group(1)) * 60 + float(m.group(2).replace(":", "."))


def parse_lrc(text: str) -> tuple[list[TimedWord], dict]:
    """Read an .lrc file. Word-level tags are used when present.

    Plain LRC only says when each line starts, so within a line the words are
    spread by syllable count -- an approximation the extractor records.
    """
    meta = {m.group(1).lower(): m.group(2).strip() for m in _META.finditer(text)}
    raw: list[tuple[float, str]] = []
    for row in text.splitlines():
        row = row.strip()
        if not row or _META.fullmatch(row):
            continue
        tags = list(_TAG.finditer(row))
        if not tags:
            continue
        body = row[tags[-1].end():].strip()
        if body:
            for t in tags:  # [00:12][01:30]same words -- a repeated chorus
                raw.append((_stamp(t), body))
    raw.sort()

    words: list[TimedWord] = []
    for i, (start, body) in enumerate(raw):
        end = raw[i + 1][0] if i + 1 < len(raw) else start + 4.0
        pieces = [p for p in _WORD_TAG.split(body)]
        if _WORD_TAG.search(body):
            # <00:12.31>through <00:12.76>days ...
            stamps = [_stamp(m) for m in _WORD_TAG.finditer(body)]
            texts = [t.strip() for t in _WORD_TAG.sub("\x00", body).split("\x00")[1:]]
            for k, (t, w) in enumerate(zip(stamps, texts)):
                if not w:
                    continue
                nxt = stamps[k + 1] if k + 1 < len(stamps) else end
                words.append(TimedWord(w, t, max(nxt, t + 0.05), i))
        else:
            ws = prosody.words(body)
            if not ws:
                continue
            counts = [len(prosody.pronunciations(w)[0]) for w in ws]
            span, at = end - start, 0.0
            for w, c in zip(ws, counts):
                d = span * c / sum(counts)
                words.append(TimedWord(w, start + at, start + at + d, i))
                at += d
    return words, meta


def to_lrc(words: list[TimedWord], meta: dict | None = None) -> str:
    """Write word-level LRC. Used to turn other sources into a karaoke file."""
    def clock(t: float) -> str:
        return f"{int(t // 60):02d}:{t % 60:05.2f}"

    out = [f"[{k}:{v}]" for k, v in (meta or {}).items()]
    by_line: dict[int, list[TimedWord]] = {}
    for w in words:
        by_line.setdefault(w.line, []).append(w)
    for i in sorted(by_line):
        ws = sorted(by_line[i], key=lambda w: w.start)
        body = " ".join(f"<{clock(w.start)}>{w.text}" for w in ws)
        out.append(f"[{clock(ws[0].start)}]{body}")
    return "\n".join(out) + "\n"


# ── YouTube ────────────────────────────────────────────────────────────────

def fetch_youtube(url: str, out_dir: str | Path, log=print) -> tuple[Path, dict]:
    """Download the audio of a YouTube URL. Returns (mp3, metadata)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    import json

    log("asking YouTube for the recording")
    info = json.loads(subprocess.run(
        ["yt-dlp", "-J", "--no-playlist", url],
        check=True, capture_output=True, text=True).stdout)
    vid = info["id"]
    mp3 = out_dir / f"{vid}.mp3"
    if not mp3.exists():
        log(f"downloading audio for {vid}")
        subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "--no-playlist", "-x", "--audio-format", "mp3",
             "-o", str(out_dir / f"{vid}.%(ext)s"), url],
            check=True, capture_output=True, text=True)
    return mp3, {"id": vid, "title": info.get("track") or info.get("title", ""),
                 "artist": info.get("artist") or info.get("uploader", ""),
                 "url": url}


_LINE_GAP_S = 0.45
_MAX_LINE_SYLLABLES = 14


def transcribe(vocals: str | Path, log=print, model: str = "small.en") -> list[TimedWord]:
    """Read the words off the separated vocal, with timings, on this machine.

    Whisper runs locally. No lyric ever goes to a hosted model -- not to
    transcribe, not to align, not to check.
    """
    from faster_whisper import WhisperModel

    log(f"transcribing the vocal locally with whisper {model} (first run downloads it)")
    wm = WhisperModel(model, device="cpu", compute_type="int8")
    segments, _ = wm.transcribe(str(vocals), word_timestamps=True, vad_filter=True,
                                beam_size=5, condition_on_previous_text=False)

    flat: list[TimedWord] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                flat.append(TimedWord(text.strip(".,!?;:\"'"), w.start, w.end, 0,
                                      round(float(w.probability), 3)))
    if not flat:
        return []

    # Lines follow the singing: a pause, or a line that has already run long.
    line, syllables = 0, 0
    out = [flat[0]]
    syllables = len(prosody.pronunciations(flat[0].text)[0])
    for prev, w in zip(flat, flat[1:]):
        n = len(prosody.pronunciations(w.text)[0])
        gap = w.start - prev.end
        if gap >= _LINE_GAP_S or (syllables + n > _MAX_LINE_SYLLABLES and gap >= 0.15):
            line += 1
            syllables = 0
        syllables += n
        out.append(TimedWord(w.text, w.start, w.end, line, w.confidence))
    return out


# ── one door for both paths ────────────────────────────────────────────────

def ingest(
    mix: str | Path,
    *,
    lrc: str | None = None,
    source_kind: str,
    work_dir: str | Path,
    log=print,
) -> tuple[Hollow, list[str], Path, Path]:
    """Recording (+ optional karaoke file) -> HOLLOW, originals, stems.

    With an .lrc the words and their timings come from the file, and we work out
    how far they sit from this particular recording. Without one we read them
    off the recording's own vocal, and the offset is zero by construction.
    """
    mix, work_dir = Path(mix), Path(work_dir)
    vocals, instrumental = separate(mix, work_dir, log=log)
    log("measuring the vocal: where it sounds, and at what pitch")
    voicing = analyse(vocals)
    dur = audio_duration(mix)
    ref = sha256(mix)
    notes: dict = {}

    if lrc is not None:
        words, _ = parse_lrc(lrc)
        if not words:
            raise ValueError("no timed lines in that karaoke file")
        shift, sure = offset_mod.estimate(
            [(w.start, w.end) for w in words], voicing, dur)
        log(f"karaoke file sits {shift:+.2f}s from this recording"
            + ("" if sure else " (uncertain — nudge it in the player)"))
        words = offset_mod.shift(words, shift)
        notes["word_timings"] = "file"
    else:
        words = transcribe(vocals, log=log)
        if not words:
            raise ValueError("no vocal found in that recording")
        shift, sure = 0.0, True
        notes["word_timings"] = "whisper"

    h, originals = build(
        words, voicing,
        song_ref=ref, duration=dur, source_kind=source_kind,
        offset_ms=int(round(shift * 1000)), offset_confident=sure, notes=notes,
    )
    log(f"HOLLOW: {len(h.lines)} lines, {h.n_slots} slots, "
        f"{sum(l.uncertain for l in h.lines)} uncertain")
    return h, originals, instrumental, mix
