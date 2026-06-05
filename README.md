# AI Karaoke

Pick a song. Pick an absurd text source. Claude rewrites the lyrics to match the song's syllable structure. Sing along in your browser with word-by-word highlighting.

## How it works

1. **Song** — pulled from [JamendoLyrics](https://github.com/f90/jamendolyrics) (20 English songs with line-level timestamps)
2. **Corpus** — any text file in `data/datasets/` (IKEA manuals, Glassdoor reviews, Trump tweets, …)
3. **Generation** — Claude rewrites the corpus to fit the song's syllable count, stress pattern, and rhyme scheme (via CMU pronouncing dict)
4. **Playback** — browser karaoke player: lyrics scroll, words highlight left-to-right in sync with audio

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI (`server.py`) |
| Frontend | Vanilla JS + Tailwind CDN (`static/index.html`) |
| Audio | JamendoLyrics MP3s streamed from HuggingFace, cached locally |
| Lyrics engine | `lyric_engine.py` — CMU pronouncing dict + Claude API |

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env.local`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Run:
```bash
python server.py
# → http://localhost:8000
```

## Project layout

```
server.py            FastAPI server — songs, generation, audio proxy
lyric_engine.py      Syllable analysis + Claude prompt builder (library)
generate_corpus.py   One-off script for adding new corpus files
static/index.html    Single-page karaoke app
data/
  datasets/          Corpus text files (one per source)
  datasets.json      Corpus metadata (id, label)
.lyric_cache/        Generated lyrics cache (gitignored)
.jamendo_cache/      Downloaded MP3s (gitignored)
```

## Adding a corpus

```bash
python generate_corpus.py <id> "<Label>" "<description>" "<style>"
# e.g.: python generate_corpus.py yelp-reviews "Yelp Reviews" "1-star restaurant yelp reviews" "angry diner"
```
