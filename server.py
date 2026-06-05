#!/usr/bin/env python3
"""AI Karaoke web server.

Usage:
    .venv/bin/python server.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path

import anthropic
import pronouncing
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from huggingface_hub import hf_hub_download
from pydantic import BaseModel

from lyric_engine import (
    build_prompt,
    build_structure,
    count_syllables,
    line_stress,
    rhyme_label,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_HF_REPO    = "jamendolyrics/jamendolyrics"
_CACHE_DIR  = Path(".jamendo_cache")
_GEN_CACHE  = Path(".lyric_cache")
_DATA_DIR   = Path("data/datasets")

app = FastAPI(title="AI Karaoke")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── helpers ────────────────────────────────────────────────────────────────────

def _hf(path: str) -> Path:
    """Download a file from the HF dataset and return its local path."""
    return Path(hf_hub_download(_HF_REPO, path, repo_type="dataset"))


def _load_songs() -> list[dict]:
    """Return English songs from JamendoLyrics, keyed by song_id."""
    index = _hf("JamendoLyrics.csv")
    songs = []
    with open(index) as f:
        for row in csv.DictReader(f):
            if row["Language"] != "English":
                continue
            song_id = Path(row["Filepath"]).stem
            songs.append({
                "id":      song_id,
                "artist":  row["Artist"],
                "title":   row["Title"],
                "genre":   row["Genre"],
                "license": row["LicenseType"],
            })
    return songs


def _load_lines(song_id: str) -> list[dict]:
    """Return [{start_ms, end_ms, text}, ...] for a song."""
    csv_path = _hf(f"annotations/lines/{song_id}.csv")
    lines = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            text = row["lyrics_line"].strip()
            if not text:
                continue
            lines.append({
                "start_ms": int(float(row["start_time"]) * 1000),
                "end_ms":   int(float(row["end_time"])   * 1000),
                "text":     text,
            })
    return lines


def _group_sections(lines: list[dict], gap_ms: int = 2500) -> list[list[dict]]:
    """Group lines into sections by timing gaps."""
    if not lines:
        return []
    sections, current = [], [lines[0]]
    for line in lines[1:]:
        if line["start_ms"] - current[-1]["end_ms"] > gap_ms:
            sections.append(current)
            current = []
        current.append(line)
    if current:
        sections.append(current)
    return sections


def _gen_cache_path(song_id: str, corpus: str) -> Path:
    key = f"jamendo|{song_id}|{corpus}".lower()
    return _GEN_CACHE / f"{hashlib.md5(key.encode()).hexdigest()[:8]}.json"


def _load_corpus_chunks(corpus: str, n_sections: int, section_sizes: list[int]) -> list[str]:
    text = (_DATA_DIR / f"{corpus}.txt").read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 60]
    total      = sum(section_sizes)
    n_paras    = len(paragraphs)
    chunks, idx = [], 0
    for i, size in enumerate(section_sizes):
        if i == len(section_sizes) - 1:
            chunk = "\n\n".join(paragraphs[idx:]) or paragraphs[-1]
        else:
            n_p   = max(1, round(size / total * n_paras))
            chunk = "\n\n".join(paragraphs[idx:idx + n_p])
            idx   = min(idx + n_p, n_paras - (len(section_sizes) - i - 1))
        chunks.append(chunk)
    return chunks


# ── routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/api/songs")
def list_songs():
    return _load_songs()


@app.get("/api/corpora")
def list_corpora():
    return json.loads(Path("data/datasets.json").read_text())


@app.get("/api/history")
def history():
    """Return previously generated Jamendo combos (have song_id + audio)."""
    songs_by_id = {s["id"]: s for s in _load_songs()}
    corpora     = {c["id"]: c["label"] for c in json.loads(Path("data/datasets.json").read_text())}
    results     = []
    for f in sorted(_GEN_CACHE.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        song_id = data.get("song_id")
        if not song_id or song_id not in songs_by_id:
            continue
        song   = songs_by_id[song_id]
        corpus = data.get("corpus", "")
        results.append({
            "song_id":      song_id,
            "artist":       song["artist"],
            "title":        song["title"],
            "genre":        song["genre"],
            "corpus":       corpus,
            "corpus_label": corpora.get(corpus, corpus),
            "n_lines":      len(data.get("lines", [])),
        })
    return results


class GenerateRequest(BaseModel):
    song_id: str
    corpus:  str


@app.post("/api/generate")
def generate(req: GenerateRequest):
    cp = _gen_cache_path(req.song_id, req.corpus)
    if cp.exists():
        return json.loads(cp.read_text())

    # Load original timed lines
    lines = _load_lines(req.song_id)
    if not lines:
        raise HTTPException(404, f"No annotations for {req.song_id}")

    corpus_path = _DATA_DIR / f"{req.corpus}.txt"
    if not corpus_path.exists():
        raise HTTPException(404, f"Corpus not found: {req.corpus}")

    # Group into sections
    sections_raw = _group_sections(lines)
    sections     = [(f"SECTION {i+1}", [l["text"] for l in sec])
                    for i, sec in enumerate(sections_raw)]

    # Build per-section corpus chunks
    section_sizes = [len(s[1]) for s in sections]
    corpus_chunks = _load_corpus_chunks(req.corpus, len(sections), section_sizes)

    # Build structural template
    structure, n_lines = build_structure(sections, corpus_chunks)
    logger.info("Generating %d lines for %s + %s", n_lines, req.song_id, req.corpus)

    # Generate with Claude
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    resp   = client.messages.create(
        model      = "claude-opus-4-6",
        max_tokens = 2500,
        messages   = [{"role": "user", "content": build_prompt(structure, n_lines)}],
    )
    generated = [l.strip() for l in resp.content[0].text.strip().splitlines() if l.strip()]
    generated = (generated + ["…"] * n_lines)[:n_lines]

    # Build result: flat list of timed lines with generated counterpart
    result_lines = []
    gen_iter     = iter(generated)
    for sec_lines in sections_raw:
        for line in sec_lines:
            result_lines.append({
                "start_ms":  line["start_ms"],
                "end_ms":    line["end_ms"],
                "original":  line["text"],
                "generated": next(gen_iter, "…"),
            })

    result = {"song_id": req.song_id, "corpus": req.corpus, "lines": result_lines}
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(result, indent=2))
    return result


@app.get("/api/audio/{song_id}")
def audio(song_id: str):
    # Cache locally — LFS files can't be fetched via hf_hub_download without auth
    cache_path = _CACHE_DIR / f"{song_id}.mp3"
    if not cache_path.exists() or cache_path.stat().st_size < 1000:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://huggingface.co/datasets/{_HF_REPO}"
            f"/resolve/main/subsets/en/mp3/{song_id}.mp3"
        )
        import httpx
        with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r:
            r.raise_for_status()
            with open(cache_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=65536):
                    f.write(chunk)
        logger.info("Downloaded %s (%.1f MB)", song_id, cache_path.stat().st_size / 1e6)
    return FileResponse(str(cache_path), media_type="audio/mpeg")


if __name__ == "__main__":
    from dotenv import load_dotenv
    for f in [".env.local", ".env"]:
        if Path(f).exists():
            for line in Path(f).read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
