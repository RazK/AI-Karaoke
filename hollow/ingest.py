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

# When a line's last word has no word after it, we know when it started and
# not when it stopped. Allow it a word's worth of time rather than stretching
# it to the next line -- a lyric that claims to be sung through every
# instrumental break cannot be lined up against a recording, and the extractor
# would read the break as one enormous held note.
_UNKNOWN_WORD_S = 1.0

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
                nxt = stamps[k + 1] if k + 1 < len(stamps) else min(
                    end, t + _UNKNOWN_WORD_S)
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
    title, artist = _tidy(info.get("title", ""), info.get("uploader", ""))
    return mp3, {"id": vid,
                 "title": info.get("track") or title,
                 "artist": info.get("artist") or artist,
                 "url": url}


_NOISE = re.compile(
    r"\s*[\(\[][^)\]]*(official|video|audio|lyric|remaster|hd|4k|mv|visualiser|"
    r"visualizer)[^)\]]*[\)\]]", re.I)


def _tidy(video_title: str, uploader: str) -> tuple[str, str]:
    """Get a song title out of a YouTube video title.

    Uploaders write "Artist - Song (Official Video) (4K Remaster)". None of that
    belongs on a card in the picker.
    """
    text = _NOISE.sub("", video_title).strip(" -–—|")
    if " - " in text:
        left, _, right = text.partition(" - ")
        return right.strip(), left.strip()
    return text, uploader


_LINE_GAP_S = 0.45
_MAX_LINE_SYLLABLES = 12


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

    # `line` holds whisper's own segment number for now: it phrases the vocal
    # into breaths, which is most of what a lyric line is.
    flat: list[TimedWord] = []
    for i, seg in enumerate(segments):
        for w in seg.words or []:
            # Store exactly the words the exam will find when it reads the line
            # back: a token whisper writes as "2" is not a syllable anyone
            # sings, and counting it would put the slots out by one. A word the
            # aligner gave no time to is one it did not place, and its
            # syllables have nowhere to go.
            found = prosody.words(w.word)
            if not found or w.end <= w.start:
                continue
            # Whisper hands back numpy scalars; the representation is a plain
            # JSON file, so they become ordinary numbers here.
            start, step = float(w.start), (float(w.end) - float(w.start)) / len(found)
            for k, text in enumerate(found):
                flat.append(TimedWord(text, start + k * step, start + (k + 1) * step,
                                      i, round(float(w.probability), 3)))
    if not flat:
        return []

    # Lines follow the singing: a new breath, a pause inside one, or a line
    # that has already run long. On a dense mix whisper returns its words
    # butted up against each other, so the pause alone finds almost nothing.
    line, syllables = 0, len(prosody.pronunciations(flat[0].text)[0])
    out = [TimedWord(flat[0].text, flat[0].start, flat[0].end, 0, flat[0].confidence)]
    for prev, w in zip(flat, flat[1:]):
        n = len(prosody.pronunciations(w.text)[0])
        gap = w.start - prev.end
        if (w.line != prev.line or gap >= _LINE_GAP_S
                or (syllables + n > _MAX_LINE_SYLLABLES and gap >= 0.15)):
            line += 1
            syllables = 0
        syllables += n
        out.append(TimedWord(w.text, w.start, w.end, line, w.confidence))
    return out


def _split_long(words: list[TimedWord], cap: int) -> list[TimedWord]:
    """Break up any line that is still too long to be one line of karaoke.

    Whisper phrases the vocal into breaths, and on a dense mix it takes very
    long ones -- two sung lines come back as one seventeen-syllable line with
    no gap anywhere in it to split on. Nobody can read that off a screen and
    nobody can write words for it, so such a line is cut at its widest internal
    pause however small that pause is.
    """
    def count(ws: list[TimedWord]) -> int:
        return sum(len(prosody.pronunciations(w.text)[0]) for w in ws)

    def cut(ws: list[TimedWord]) -> list[list[TimedWord]]:
        if count(ws) <= cap or len(ws) < 4:
            return [ws]
        total, best, at = count(ws), None, len(ws) // 2
        for k in range(2, len(ws) - 1):
            # the widest pause, nudged towards an even split
            score = (ws[k].start - ws[k - 1].end) + 0.15 * (
                1 - abs(count(ws[:k]) - count(ws[k:])) / total)
            if best is None or score > best:
                best, at = score, k
        return cut(ws[:at]) + cut(ws[at:])

    by_line: dict[int, list[TimedWord]] = {}
    for w in words:
        by_line.setdefault(w.line, []).append(w)
    out, line = [], 0
    for i in sorted(by_line):
        for piece in cut(by_line[i]):
            out += [TimedWord(w.text, w.start, w.end, line, w.confidence) for w in piece]
            line += 1
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

    # Whichever door the words came through, a line has to be one line of
    # karaoke: short enough to read off a screen and to write words for. Some
    # karaoke files phrase a whole rapped verse as one thirty-syllable line.
    words = _split_long(words, _MAX_LINE_SYLLABLES)

    h, originals = build(
        words, voicing,
        song_ref=ref, duration=dur, source_kind=source_kind,
        offset_ms=int(round(shift * 1000)), offset_confident=sure, notes=notes,
    )
    log(f"HOLLOW: {len(h.lines)} lines, {h.n_slots} slots, "
        f"{sum(l.uncertain for l in h.lines)} uncertain")
    return h, originals, instrumental, mix
