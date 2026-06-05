# AI Karaoke — agent guide

## What this is

Browser karaoke app: pick a JamendoLyrics song + text corpus → Claude rewrites lyrics to match syllable/stress structure → play back with word-by-word highlight.

## Stack

- **`server.py`** — FastAPI. Endpoints: `GET /api/songs`, `GET /api/corpora`, `GET /api/history`, `POST /api/generate`, `GET /api/audio/{song_id}`
- **`lyric_engine.py`** — pure library (no CLI). Exports: `line_stress`, `count_syllables`, `rhyme_label`, `build_structure`, `build_prompt`
- **`static/index.html`** — single-file vanilla JS + Tailwind CDN. No build step.
- **`data/datasets/`** — corpus `.txt` files. `data/datasets.json` is the manifest.
- **`.lyric_cache/`** — JSON cache of generated lyrics, keyed by `md5(jamendo|{song_id}|{corpus})`
- **`.jamendo_cache/`** — downloaded MP3s

## Working rules

1. **Human-in-the-loop** — no unattended runs; commit only when the user asks
2. **No build step** — `static/index.html` is served as-is; Tailwind via CDN
3. **Docs ↔ code** — update README / AGENTS when behaviour or layout changes
4. **Never commit** `.env.local`, cache dirs, or `__pycache__`

## Key design decisions

- Audio is streamed from HuggingFace LFS URLs (`/resolve/main/subsets/en/mp3/{id}.mp3`) and cached locally — `hf_hub_download` returns LFS pointers, not the actual file
- Word highlighting uses JS color interpolation at 60 fps (no CSS transitions on color — they conflict with rAF updates)
- Smooth scroll uses a custom rAF loop that cancels the previous animation before starting a new one
- The pre-song countdown is rendered as the first DOM element inside `#lyrics-inner` (in the lyrics flow, above line 0) so it sits naturally one slot above the first lyric

## Corpus format

Plain text, paragraphs separated by blank lines. Paragraphs shorter than 60 chars are skipped. The engine distributes paragraphs across song sections proportionally by line count.
