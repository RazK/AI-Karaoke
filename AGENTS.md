# AI Karaoke — Agent Coordination

This file is the single source of truth for all parallel agent work.
**Every agent reads this entire file before starting. Then follow only your section.**

> Next.js note: this version may have breaking changes from your training data.
> Read the relevant guide in `node_modules/next/dist/docs/` before writing any Next.js code.

---

## Project in one paragraph

Party karaoke app. A host picks a song + a "dataset" (IKEA manuals, Yelp 1-star reviews, etc.).
The AI rewrites the song's lyrics using words from that dataset, syllable-for-syllable matched
to the original. The karaoke screen plays the YouTube video and highlights words in sync.
The hard problems are: (1) reliable syllable-matched lyric generation, (2) word-level timing.
Neither is solved yet. The UI is a draft placeholder.

Full architecture: `docs/SDD.md` | Scope: `docs/SRS.md` | UX flows: `docs/UX.md` | API spec: `docs/API.md`

---

## Current codebase state

| Area | Status | Notes |
|------|--------|-------|
| Next.js scaffold | ✅ done | Picker, Generating, Karaoke screens exist as draft |
| UI implementation | ⚠️ draft | `app/ui/v1/` — owner not satisfied, do not extend |
| `/api/generate` route | ❌ not built | `app/api/` does not exist yet |
| Python generate CLI | ❌ not built | `scripts/` does not exist yet |
| Word-level timing | ❌ not built | LRC files have line timing only |
| YouTube IFrame player | ❌ not built | Phase 3 |

---

## Branch strategy

```
main
  ├── agent/A-lyric-generation      ← Agent A works here
  ├── agent/B-word-timing           ← Agent B works here
  ├── agent/C-api-route             ← Agent C works here (after A merges)
  ├── agent/D-timing-integration    ← Agent D works here (after B merges)
  └── ui/v2                         ← UI agent works here (after A+B+C+D merge)
```

- Branch from `main` unless your section says otherwise
- PR back to `main` when done
- Agents never commit to each other's branches
- PRs must pass `npm run build` (Next.js agents) or `python scripts/test_generate.py` (Python agents)

---

## File ownership — hard boundaries

| Path | Owner | Everyone else |
|------|-------|---------------|
| `scripts/` | Agent A, Agent B | ❌ DO NOT TOUCH |
| `app/api/` | Agent C | ❌ DO NOT TOUCH |
| `data/lrc/` | Agent B adds `*-words.json` | read-only |
| `data/songs.json`, `data/datasets.json` | read-only for all | — |
| `app/ui/v1/` | frozen | ❌ DO NOT TOUCH |
| `app/components/` | frozen | ❌ DO NOT TOUCH |
| `app/types.ts` | any agent may ADD fields, never remove/rename | careful |
| `docs/` | read freely; update only your own section | careful |
| `AGENTS.md` | update only your Status line | — |

---

## Rules all agents follow

1. **Read `docs/API.md`** before writing anything that touches lyric data shapes.
2. **Syllable counts are sacred.** `sum(generated[i].syllables)` must equal `line.syllableCount` with zero tolerance. See `docs/API.md`.
3. **Never touch `app/ui/v1/` or `app/components/`.** UI is a separate concern.
4. **Show your output.** Before opening a PR, paste one real example of the thing working.
5. **Small commits, clear messages.** Do not squash history.
6. **Open PR as draft first**, describe what you tested, then mark ready for review.

---

## Agent A — Lyric Generation CLI

**Branch:** `agent/A-lyric-generation`
**Status:** NOT STARTED
**Can start:** immediately — no dependencies

### Job

Build a Python CLI that proves the core lyric-generation algorithm works before any
server or UI code is written around it. The prompt it validates becomes the source of
truth for Agent C.

### Setup

```bash
mkdir scripts && cd scripts
pip install anthropic pyphen
```

Create `scripts/requirements.txt`.

### Build `scripts/generate.py`

```bash
python scripts/generate.py --song bohemian-rhapsody --dataset ikea-manuals
# Prints validated LyricLine[] JSON to stdout
# Also writes scripts/output/<song>-<dataset>.json
```

Steps:
1. Load `data/lrc/<songId>.json` — get lines with text
2. Count syllables per word using `pyphen` (see below)
3. Load dataset corpus (start with a hardcoded IKEA-style paragraph; real corpus files come later)
4. Build prompt per `docs/API.md § Prompt Strategy`
5. Call `anthropic.Anthropic().messages.create()` with `claude-sonnet-4-5`
6. Parse JSON response
7. Validate: `sum(w['syllables'] for w in line['generated']) == line['syllableCount']` for every line
8. On any failure: retry with an amended prompt noting exactly which lines failed and by how much (max 3 retries)
9. After 3 failures: print error and exit 1

### Syllable counting

```python
import pyphen
dic = pyphen.Pyphen(lang='en_US')

def count_syllables(word: str) -> int:
    clean = word.strip(".,!?;:-'\"").lower()
    if not clean:
        return 1
    positions = dic.positions(clean)
    return len(positions) + 1 if positions else 1
```

Use this for annotating original lyrics AND validating generated output.

### Done when

Run `python scripts/generate.py --song bohemian-rhapsody --dataset ikea-manuals` three times.
All three produce valid JSON with zero syllable mismatches.

### PR must include

- The final prompt (verbatim — Agent C will copy it exactly)
- One full JSON output pasted in the description
- Observed retry rate across your test runs
- Any songs/datasets where it struggled

---

## Agent B — Word-Level Timing Pipeline

**Branch:** `agent/B-word-timing`
**Status:** NOT STARTED
**Can start:** immediately — runs in parallel with Agent A

### Job

LRC files give line-start timestamps. We need per-word timestamps for frame-accurate
karaoke highlighting. Build a pipeline: YouTube audio → word timestamps JSON.

### Setup

```bash
pip install whisperx yt-dlp
```

### Build `scripts/align.py`

```bash
python scripts/align.py --youtube-id tAGnKpE4NCI --song bohemian-rhapsody
# Produces data/lrc/bohemian-rhapsody-words.json
```

Steps:
1. Download audio: `yt-dlp -x --audio-format mp3 -o /tmp/<songId>.mp3 "https://youtube.com/watch?v=<youtubeId>"`
2. Run WhisperX with forced alignment
3. Parse WhisperX output (word-level segments with start/end in seconds)
4. Convert to milliseconds
5. Write output file

### Output format (`data/lrc/<songId>-words.json`)

```json
{
  "songId": "bohemian-rhapsody",
  "words": [
    { "word": "Is",   "startMs": 4200, "endMs": 4450 },
    { "word": "this", "startMs": 4450, "endMs": 4620 }
  ]
}
```

Do not change this format after your PR is open — Agent D depends on it.

### Done when

`data/lrc/bohemian-rhapsody-words.json` exists covering at least the first 60 seconds.
Spot-check: play YouTube, pause at t=30s, verify the words in JSON for t=28-32s
match what's being sung.

### PR must include

- WhisperX command that worked
- Table of 10 sample words with timestamps — do they look right?
- Any alignment problems observed

---

## Agent C — `/api/generate` Route

**Branch:** `agent/C-api-route`
**Status:** BLOCKED — start after Agent A's PR merges
**Depends on:** Agent A

### Job

Wrap Agent A's validated prompt in a Next.js serverless function.
Full spec in `docs/API.md` — read it entirely first.

### Build `app/api/generate/route.ts`

- `POST /api/generate` accepts `{ songId, datasetId, bustCache }`
- Copy Agent A's final prompt **verbatim** from their PR — do not rewrite it
- Validate every line with zero tolerance (same rule as Agent A)
- Retry up to 3 times on mismatch
- `ANTHROPIC_API_KEY` from `process.env` only — never in client code
- Return `{ lines: LyricLine[] }` or `{ error: string }` with appropriate status codes

### Done when

```bash
curl -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"songId":"bohemian-rhapsody","datasetId":"ikea-manuals"}'
```

Returns valid syllable-matched JSON. Run 3 times, all succeed.

### PR must include

- Sample response JSON
- Confirmation that `ANTHROPIC_API_KEY` is not logged or returned to client

---

## Agent D — Timing Integration

**Branch:** `agent/D-timing-integration`
**Status:** BLOCKED — start after Agent B's PR merges
**Depends on:** Agent B

### Job

Replace the fake proportional word-timing in the karaoke screen with Agent B's real timestamps.

### What to change

`app/ui/v1/KaraokeScreen.tsx` — timing logic only:
- Load `data/lrc/<songId>-words.json`
- Drive `highlightedWordIndex` from `currentMs` vs real `startMs`/`endMs` per word
- Do not change any visual design — only the timing logic

### Done when

With bohemian-rhapsody: at `currentMs = 4200`, "Is" is highlighted.
At `currentMs = 4720`, "real" is highlighted. Timing matches Agent B's data exactly.

---

## Agent UI — New UI (future)

**Branch:** `ui/v2`
**Status:** DO NOT START until A + B + C + D are all merged

### Job

Replace `app/ui/v1/` entirely. Read `docs/UX.md` for the interaction spec.
Do not look at `app/ui/v1/` for inspiration — start from the spec.

Use v0.dev (https://v0.dev) to generate whole screens from the UX descriptions.
Wire them to the real `/api/generate` route and the word-timing data.
Interfaces to implement are in `app/types.ts`.
