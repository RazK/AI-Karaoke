#!/usr/bin/env python3
"""The stage.

Runs locally. Nothing here knows whether a song arrived as a karaoke file or as
a YouTube URL -- by the time the player sees it, both are a HOLLOW file, an
instrumental and a set of words.
"""
from __future__ import annotations

import json
import sys
import threading
import traceback
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hollow.dress import Dressing, anthropic_writer, dress
from hollow.grade import grade
from hollow.library import Library
from hollow.timing import word_times

ROOT = Path(__file__).resolve().parent
DATA = Path("data/datasets")
UPLOADS = Path(".work/uploads")

app = FastAPI(title="AI Karaoke")
lib = Library()


# ── jobs ───────────────────────────────────────────────────────────────────
#
# Ingesting a song takes minutes: a download, source separation, and a local
# transcription. The one thing the screen must never do is sit there saying
# nothing, so every slow call runs as a job that reports what it is doing.

JOBS: dict[str, dict] = {}


def start_job(what: str, fn) -> str:
    job_id = uuid.uuid4().hex[:8]
    JOBS[job_id] = {"state": "running", "what": what, "log": [], "result": None}

    def log(message: str) -> None:
        JOBS[job_id]["log"].append(str(message))

    def run() -> None:
        try:
            JOBS[job_id]["result"] = fn(log)
            JOBS[job_id]["state"] = "done"
        except Exception as exc:  # surfaced to the screen, not swallowed
            traceback.print_exc()
            JOBS[job_id]["state"] = "failed"
            JOBS[job_id]["error"] = str(exc) or exc.__class__.__name__

    threading.Thread(target=run, daemon=True).start()
    return job_id


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "no such job")
    j = JOBS[job_id]
    return {"state": j["state"], "what": j["what"], "log": j["log"][-8:],
            "result": j.get("result"), "error": j.get("error")}


# ── library ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/songs")
def songs():
    return [s.__dict__ for s in lib.songs()]


@app.get("/api/corpora")
def corpora():
    rows = json.loads(Path("data/datasets.json").read_text())
    return [r for r in rows if (DATA / f"{r['id']}.txt").exists()]


@app.get("/api/song/{ref}")
def song(ref: str):
    s = lib.get(ref)
    if not s:
        raise HTTPException(404, "no such song")
    h = lib.hollow(ref)
    originals = lib.originals(ref)
    owords = word_times(h, originals) if originals else []
    return {
        "song": s.__dict__,
        "lines": [
            {"id": l.id, "group": l.group, "start": l.start, "end": l.end,
             "slots": len(l.slots), "uncertain": l.uncertain,
             "original": originals[l.id] if l.id < len(originals) else "",
             # The original's words on the same slots the rewrite uses, so the
             # player can light both in step and you can see which new word
             # goes where the old one went.
             "owords": owords[l.id] if l.id < len(owords) else []}
            for l in h.lines
        ],
        "dressings": [d["name"] for d in lib.dressings(ref)],
    }


@app.get("/api/song/{ref}/dressing/{name}")
def dressing(ref: str, name: str):
    for d in lib.dressings(ref):
        if d["name"] == name:
            return d
    raise HTTPException(404, "not generated")


@app.get("/api/audio/{ref}")
def audio(ref: str, track: str = "instrumental"):
    path = lib.dir(ref) / f"{'mix' if track == 'mix' else 'instrumental'}.mp3"
    if not path.exists():
        raise HTTPException(404, "no audio")
    return FileResponse(path, media_type="audio/mpeg")


# ── getting a song in ──────────────────────────────────────────────────────

class YouTubeRequest(BaseModel):
    url: str
    title: str = ""
    artist: str = ""


@app.post("/api/ingest/youtube")
def ingest_youtube(req: YouTubeRequest):
    def work(log):
        from hollow.ingest import fetch_youtube, ingest

        mp3, meta = fetch_youtube(req.url, UPLOADS, log=log)
        h, originals, instrumental, mix = ingest(
            mp3, lrc=None, source_kind="youtube",
            work_dir=Path(".work") / meta["id"], log=log)
        s = lib.add(h, originals, title=req.title or meta["title"],
                    artist=req.artist or meta["artist"],
                    instrumental=instrumental, mix=mix, source_ref=req.url)
        return {"ref": s.ref, "title": s.title, "artist": s.artist}

    return {"job": start_job("Fetching from YouTube", work)}


@app.post("/api/ingest/karaoke")
async def ingest_karaoke(lrc: UploadFile, audio: UploadFile,
                         title: str = Form(""), artist: str = Form("")):
    UPLOADS.mkdir(parents=True, exist_ok=True)
    lrc_text = (await lrc.read()).decode("utf-8", "replace")
    audio_path = UPLOADS / (audio.filename or "upload.mp3")
    audio_path.write_bytes(await audio.read())

    def work(log):
        from hollow.ingest import ingest

        h, originals, instrumental, mix = ingest(
            audio_path, lrc=lrc_text, source_kind="karaoke_file",
            work_dir=Path(".work") / audio_path.stem, log=log)
        s = lib.add(h, originals, title=title or audio_path.stem, artist=artist,
                    instrumental=instrumental, mix=mix,
                    source_ref=lrc.filename or "")
        return {"ref": s.ref, "title": s.title, "artist": s.artist}

    return {"job": start_job("Reading the karaoke file", work)}


# ── generating ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    ref: str
    corpus: str = ""  # id of a bundled corpus
    text: str = ""  # or text pasted straight in
    name: str = ""
    licence: float = 0.0


@app.post("/api/generate")
def generate(req: GenerateRequest):
    s = lib.get(req.ref)
    if not s:
        raise HTTPException(404, "no such song")
    if req.text.strip():
        corpus_text, corpus_name = req.text, (req.name or "pasted text")
    else:
        path = DATA / f"{req.corpus}.txt"
        if not path.exists():
            raise HTTPException(404, f"no corpus called {req.corpus}")
        corpus_text, corpus_name = path.read_text(encoding="utf-8"), req.corpus
    licence = max(0.0, min(1.0, req.licence))

    name = f"{_slug(corpus_name)}-{int(round(licence * 100)):03d}"
    if any(d["name"] == name for d in lib.dressings(req.ref)):
        return {"job": start_job("Already made — opening it",
                                 lambda log: {"ref": req.ref, "name": name})}

    def work(log):
        import os

        writer = None
        if licence > 0 and os.environ.get("ANTHROPIC_API_KEY"):
            writer = anthropic_writer()
        elif licence > 0:
            log("no ANTHROPIC_API_KEY — falling back to what the corpus itself offers")

        h = lib.hollow(req.ref)
        log(f"looking for phrases in {corpus_name} that fit the tune")
        d = dress(h, corpus_text, licence, corpus_name=corpus_name,
                  writer=writer, log=log)
        log("scoring it")
        card = grade(h, d, corpus_text, lib.originals(req.ref), writer=writer)
        payload = _payload(name, h, d, card)
        lib.save_dressing(req.ref, name, payload)
        log(f"{card.singable:.2f}/10, {len(d.bends)} bent lines")
        return {"ref": req.ref, "name": name}

    return {"job": start_job(f"Dressing {corpus_name} onto the tune", work)}


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:40]


def _payload(name: str, h, d: Dressing, card) -> dict:
    return {
        "name": name,
        **d.to_dict(),
        "words": word_times(h, d.lines),
        "card": {
            "singable": round(card.singable, 2),
            "unsingable": card.unsingable,
            "corpus_fidelity": round(card.corpus_fidelity, 3),
            "corpus_note": card.corpus_note,
            "register_distance": round(card.register_distance, 2),
            "register_parts": {k: round(v, 2) for k, v in card.register_parts.items()},
            "grammar": round(card.grammar, 3),
            "grammar_note": card.grammar_note,
            "bad_lines": card.bad_lines,
            "honesty": round(card.honesty, 3),
            "undeclared_bends": card.undeclared_bends,
            "excluded": card.excluded,
            "exam": {"fit": round(card.exam.fit, 3), "stress": round(card.exam.stress, 3),
                     "rhyme": round(card.exam.rhyme, 3), "vowel": round(card.exam.vowel, 3)},
        },
    }


# ── what Raz thinks ────────────────────────────────────────────────────────

class Rating(BaseModel):
    ref: str
    dressing: str
    stars: float


@app.post("/api/rate")
def rate(r: Rating):
    d = dressing(r.ref, r.dressing)
    return lib.rate(r.ref, r.dressing, r.stars, d["card"]["singable"])


@app.get("/api/disagreements")
def disagreements():
    """Songs where Raz and the exam disagree by more than two points.

    A disagreement means the exam is measuring the wrong thing. Nothing is
    refitted automatically -- the weights are a starting point, not an answer.
    """
    titles = {s.ref: f"{s.title} — {s.artist}" for s in lib.songs()}
    return [dict(r, song=titles.get(r["ref"], r["ref"])) for r in lib.disagreements()]


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


if __name__ == "__main__":
    import os

    for f in (".env.local", ".env"):
        if Path(f).exists():
            for row in Path(f).read_text().splitlines():
                if "=" in row and not row.startswith("#"):
                    k, _, v = row.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    uvicorn.run(app, host="127.0.0.1", port=8000)
