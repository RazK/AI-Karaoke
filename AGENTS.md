# AI Karaoke — Agent Coordination

This file is the single source of truth for all parallel agent work.
**Every agent reads this entire file before starting. Then follow only your section.**

> Next.js note: this version may have breaking changes from your training data.
> Read the relevant guide in `node_modules/next/dist/docs/` before writing any Next.js code.

---

## Overnight / Unattended Run Guide

**Read this first. It is mandatory for any session that runs without a human watching.**

### What you are allowed to do without asking

- Install any Python package via pip
- Install any npm package (check package.json first for an existing equivalent)
- Create files anywhere in the repo
- Run scripts that take minutes or hours
- Make as many API calls as needed (the key is pre-authorised)
- Commit and push at any time
- Open a GitHub PR when done

### What you must never do without asking

- Delete files (create new ones instead)
- Modify `app/ui/v1/` or `app/components/`
- Change `app/types.ts` field names or types (you may add new optional fields)
- Merge PRs yourself
- Push to `main` or `feat/nextjs-scaffold` directly (open a PR instead)
- Spend money beyond standard API calls (no paid third-party services)

### One-time setup the user does before sleeping

The user must do these once before starting an overnight session. They do not require agent action:

1. **Set `ANTHROPIC_API_KEY`** in the Claude Code environment settings (Settings → Environment Variables). This key is used by Agent A and Agent C to call the Claude API.
2. **Verify network policy** allows outbound HTTPS. Agent B needs to download audio from YouTube and ML model weights.

That's it. Agents handle everything else.

### Pre-flight check — run this before anything else

```bash
echo "=== PRE-FLIGHT ===" > logs/agent-STATUS.md

# 1. API key — load from .env.local if not already in environment
if [ -z "$ANTHROPIC_API_KEY" ] && [ -f ".env.local" ]; then
  export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env.local | cut -d= -f2-)
fi
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "FATAL: ANTHROPIC_API_KEY is not set and .env.local not found." >> logs/agent-STATUS.md
  git add logs/ && git commit -m "agent: STOPPED — ANTHROPIC_API_KEY missing" && git push
  exit 1
fi
echo "ANTHROPIC_API_KEY: present (${ANTHROPIC_API_KEY:0:8}...)" >> logs/agent-STATUS.md

# 2. Git
echo "Git remote: $(git remote get-url origin)" >> logs/agent-STATUS.md
echo "Current branch: $(git branch --show-current)" >> logs/agent-STATUS.md

# 3. Network
curl -s --max-time 10 https://api.anthropic.com > /dev/null \
  && echo "Network: OK" >> logs/agent-STATUS.md \
  || echo "Network: WARN — could not reach api.anthropic.com" >> logs/agent-STATUS.md

git add logs/ && git commit -m "agent: pre-flight passed" && git push
```

If pre-flight fails, stop. Do not proceed. The status file tells the user what to fix.

### Progress logging — mandatory throughout

Maintain `logs/agent-<LETTER>-status.md` and update it continuously.
**Commit and push after every major step.** Do not batch work and push at the end.
If the cloud session times out, only pushed commits are saved.

Commit message format: `agent-A: <what just completed>`

### When you are completely done

Write `logs/agent-<LETTER>-DONE.md` with:
- Summary of what was built
- How to verify it works (one command)
- What the next agent (if any) needs to know
- Anything unexpected that happened
- Any open questions for the human

Commit it, push it, open a PR into `main`.

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
main                                ← base branch — branch from here, PR back here
  ├── agent/A-lyric-generation
  ├── agent/B-word-timing
  ├── agent/C-api-route             (start after A merges)
  └── agent/D-timing-integration    (start after B merges)
```

**Branch from `main`.** Main now has the full app (Next.js scaffold merged in).

Setup your branch:
```bash
git fetch origin
git checkout main
git pull origin main
git checkout -b agent/A-lyric-generation   # use your agent's branch name
git push -u origin agent/A-lyric-generation
```

---

## File ownership — hard boundaries

| Path | Owner | Everyone else |
|------|-------|---------------|
| `scripts/` | Agent A, Agent B | ❌ DO NOT TOUCH |
| `app/api/` | Agent C | ❌ DO NOT TOUCH |
| `data/lrc/` | Agent B adds `*-words.json` | read-only |
| `data/songs.json`, `data/datasets.json` | all agents read | do not modify |
| `app/ui/v1/` | frozen | ❌ DO NOT TOUCH |
| `app/components/` | frozen | ❌ DO NOT TOUCH |
| `app/types.ts` | any agent may ADD optional fields | never remove/rename |
| `logs/` | your agent writes here | do not delete others' logs |
| `docs/` | read freely; do not modify | — |
| `AGENTS.md` | update only your Status line when done | — |

---

## Agent A — Lyric Generation CLI

**Branch:** `agent/A-lyric-generation`
**Status:** NOT STARTED
**Can start:** immediately — no dependencies
**Estimated time:** 2–4 hours including iteration

### Your job

Build and validate the Python CLI that generates syllable-matched lyrics.
The prompt you land on becomes the source of truth for Agent C — write it clearly.
This is the most important piece of work. Take the time to get it right.

### Setup

```bash
git checkout -b agent/A-lyric-generation
git push -u origin agent/A-lyric-generation
mkdir -p scripts/output logs
pip install anthropic pyphen
echo "anthropic\npyphen" > scripts/requirements.txt
```

### Syllable counting — use this everywhere

```python
import pyphen
import re

_dic = pyphen.Pyphen(lang='en_US')

def count_syllables(word: str) -> int:
    """Count syllables in a single word. Strip punctuation first."""
    clean = re.sub(r"[^a-zA-Z']", '', word).lower()
    if not clean:
        return 1
    positions = _dic.positions(clean)
    return len(positions) + 1 if positions else 1
```

Use this for BOTH annotating the original lyrics AND validating the generated output.
Never trust the `syllableCount` field in LRC files — always recount from the words.

### Build `scripts/generate.py`

```bash
python scripts/generate.py --song bohemian-rhapsody --dataset ikea-manuals
```

Steps the script must do, in order:

**Step 1: Load and annotate original lyrics**
- Load `data/lrc/<songId>.json`
- For each line, split the text into words and count syllables with `count_syllables()`
- Compute `syllableCount` from the actual words (do not trust the stored value)
- Log the annotated lines to `logs/agent-A-status.md` for inspection

**Step 2: Load dataset corpus**
- For now, use a hardcoded string of IKEA-style instruction text (~500 words)
- Later this will load from `data/datasets/<datasetId>.txt`

**Step 3: Build prompt and call Claude API**

Use this exact prompt structure (do not improvise — iterate on this):

```
You are rewriting song lyrics using text from a provided corpus.

RULES — follow all of them exactly:
1. Every generated line MUST have EXACTLY the same syllable count as the original.
   Count carefully. Before writing each line:
   a. Count the syllables in the original
   b. Write your generated words
   c. Count again and verify the sums match
   If they don't match, rewrite the line.
2. Take words and phrases from the provided corpus. Adapt lightly but stay close.
3. Preserve end-rhymes if possible. Never at the cost of rule 1.
4. Return ONLY valid JSON. No commentary, no code fences, no markdown.

SYLLABLE VERIFICATION EXAMPLE:
  original: [{"word":"No","syllables":1},{"word":"es-cape","syllables":2},
             {"word":"from","syllables":1},{"word":"re-al-i-ty","syllables":4}]
  sum = 1+2+1+4 = 8
  good generated (sum=8):
  [{"word":"In-sert","syllables":2},{"word":"screw","syllables":1},
   {"word":"type","syllables":1},{"word":"A","syllables":1},
   {"word":"care-ful-ly","syllables":3}]  → 2+1+1+1+3 = 8 ✓
  bad generated (sum=9, adds extra word):
  [..."here"(1),"care-ful-ly"(3)] → 9 ✗  WRONG, rewrite.

OUTPUT FORMAT — return a JSON array, nothing else:
[
  {
    "lineIndex": 0,
    "syllableCount": 5,
    "original":  [{"word": "Is",  "syllables": 1}, ...],
    "generated": [{"word": "Fix", "syllables": 1}, ...]
  },
  ...
]

--- ORIGINAL LYRICS (annotated with syllable counts) ---
{annotated_lyrics_json}

--- CORPUS ---
{corpus_text}
```

**Step 4: Parse and validate**

```python
import json, anthropic

def validate_lines(lines: list) -> list[str]:
    """Return list of error strings. Empty list = all good."""
    errors = []
    for line in lines:
        orig_sum = sum(w['syllables'] for w in line['original'])
        gen_sum  = sum(w['syllables'] for w in line['generated'])
        if orig_sum != gen_sum:
            errors.append(
                f"Line {line['lineIndex']}: original={orig_sum} syllables, "
                f"generated={gen_sum} syllables — MISMATCH"
            )
    return errors
```

**Step 5: Retry loop**

```python
MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    response = call_claude(prompt)
    lines = json.loads(response)
    errors = validate_lines(lines)
    if not errors:
        break
    # Add error feedback to prompt and retry
    prompt += f"\n\nPREVIOUS ATTEMPT FAILED. Fix these specific lines:\n" + "\n".join(errors)
    log(f"Attempt {attempt+1} failed: {errors}")

if errors:
    log("FAILED after 3 attempts — writing partial results")
    # still write what we have, mark as failed
```

**Step 6: Write output**

```python
# stdout (for piping)
print(json.dumps(lines, indent=2))

# file (for inspection)
Path(f"scripts/output/{song_id}-{dataset_id}.json").write_text(json.dumps(lines, indent=2))
```

### Iteration guidance

Run the script. Look at the output. If syllable matching is failing frequently:
- Try making the prompt more explicit about the counting step
- Try asking for chain-of-thought in a scratchpad field (then strip it from output)
- Try `claude-opus-4-7` if `claude-sonnet-4-5` is struggling (higher cost but better compliance)

Keep all prompt versions in `scripts/prompt_versions/` with notes on what improved.

### Done when

Run `python scripts/generate.py --song bohemian-rhapsody --dataset ikea-manuals` five times.
At least 4 of 5 must produce zero syllable mismatches on first attempt (no retries).
Write all 5 results to `scripts/output/` for the PR.

### Commit cadence

```bash
# After setup
git add scripts/ && git commit -m "agent-A: scaffold generate.py" && git push

# After each working version
git add . && git commit -m "agent-A: prompt v2 — 60% pass rate" && git push

# When done
git add . && git commit -m "agent-A: DONE — 5/5 pass, prompt finalized" && git push
```

### PR description must include

- The final prompt (complete, verbatim — Agent C copies it exactly)
- Pass rate observed across all runs
- Sample output for 2 different song+dataset combos (paste the full JSON)
- Which Claude model was used and why

---

## Agent B — Word-Level Timing Pipeline

**Branch:** `agent/B-word-timing`
**Status:** NOT STARTED
**Can start:** immediately — runs in parallel with Agent A
**Estimated time:** 3–6 hours (model downloads are slow)

### Your job

LRC files give us when a LINE starts. We need when each WORD starts, to the millisecond.
Build a pipeline: YouTube song → per-word timestamps JSON.
This replaces the current fake proportional timing in the karaoke screen.

### Setup

```bash
git checkout -b agent/B-word-timing
git push -u origin agent/B-word-timing
mkdir -p scripts logs data/lrc
pip install openai-whisper yt-dlp
echo "openai-whisper\nyt-dlp" > scripts/requirements-B.txt
```

Note: `openai-whisper` downloads model weights on first use (~140MB for `base`, ~460MB for `medium`).
This is normal. It will be slow the first time, fast after.

### Build `scripts/align.py`

```bash
python scripts/align.py --youtube-id tAGnKpE4NCI --song bohemian-rhapsody
# Produces: data/lrc/bohemian-rhapsody-words.json
```

#### Step 1: Download audio

```python
import subprocess, os

def download_audio(youtube_id: str, song_id: str) -> str:
    out_path = f"/tmp/{song_id}.mp3"
    if os.path.exists(out_path):
        return out_path  # already downloaded
    subprocess.run([
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", out_path,
        f"https://www.youtube.com/watch?v={youtube_id}"
    ], check=True)
    return out_path
```

#### Step 2: Transcribe with word timestamps

```python
import whisper

def transcribe_with_words(audio_path: str) -> list[dict]:
    """Returns list of {word, start, end} in seconds."""
    model = whisper.load_model("base")   # use "medium" if accuracy is poor
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en"
    )
    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({
                "word":    w["word"].strip(),
                "startMs": int(w["start"] * 1000),
                "endMs":   int(w["end"]   * 1000),
            })
    return words
```

#### Step 3: Write output

Output format — do not change this schema after your PR is open (Agent D depends on it):

```python
import json
from pathlib import Path

def write_output(song_id: str, words: list[dict]):
    data = {"songId": song_id, "words": words}
    path = Path(f"data/lrc/{song_id}-words.json")
    path.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(words)} words to {path}")
```

Final output example:
```json
{
  "songId": "bohemian-rhapsody",
  "words": [
    { "word": "Is",   "startMs": 4210, "endMs": 4420 },
    { "word": "this", "startMs": 4420, "endMs": 4590 },
    { "word": "the",  "startMs": 4590, "endMs": 4680 },
    { "word": "real", "startMs": 4680, "endMs": 4950 },
    { "word": "life", "startMs": 4950, "endMs": 5180 }
  ]
}
```

#### Step 4: Spot-check

After generating, write a spot-check report comparing timestamps to known LRC line starts.
Example: LRC says line "Is this the real life?" starts at ~4200ms.
Whisper's first word "Is" should start near 4200ms. If it's off by more than 500ms, try `medium` model.

### Accuracy notes

- `base` model: fast, ~60% word accuracy, timing within ~100ms — good enough for v1
- `medium` model: slow (~3x), ~80% word accuracy, timing within ~50ms — better
- Start with `base`. If spot-check shows >500ms drift, rerun with `medium`.
- CPU inference on `medium` for a 6-minute song takes ~30-60 minutes. This is fine overnight.

### If yt-dlp fails (network/YouTube block)

Some cloud environments block YouTube. Test first:
```bash
yt-dlp --simulate https://www.youtube.com/watch?v=tAGnKpE4NCI
```
If it fails, write this to your status log. Then generate SYNTHETIC timestamps as a fallback:
```python
# Fallback: space words evenly within each LRC line's time window
# Load data/lrc/bohemian-rhapsody.json, distribute words across each line's duration
```
Document which approach you used in the PR.

### Commit cadence

```bash
git add . && git commit -m "agent-B: setup + yt-dlp test" && git push
git add . && git commit -m "agent-B: base model done, spot-check OK" && git push
git add . && git commit -m "agent-B: DONE — words written for bohemian-rhapsody" && git push
```

### PR description must include

- Which Whisper model you used and why
- Spot-check table: 10 words with timestamps vs expected timing (from LRC lines)
- Whether yt-dlp worked or fallback was needed
- The word JSON for at least the first 60 seconds of bohemian-rhapsody

---

## Agent C — `/api/generate` Route

**Branch:** `agent/C-api-route`
**Status:** BLOCKED — start only after Agent A's PR is merged into `main`
**Depends on:** Agent A
**Estimated time:** 2–3 hours

### Your job

Wrap Agent A's validated prompt in a Next.js serverless function.
Read `docs/API.md` entirely before writing a line of code.

### Setup

```bash
git fetch origin
git checkout main && git pull
git checkout -b agent/C-api-route
git push -u origin agent/C-api-route
mkdir -p app/api/generate logs
```

### Build `app/api/generate/route.ts`

- `POST /api/generate` accepts `{ songId, datasetId, bustCache }`
- Copy Agent A's final prompt **verbatim** — do not rewrite or improve it
- Validate every line: `sum(generated.syllables) === syllableCount`, zero tolerance
- Retry up to 3 times on any mismatch
- `ANTHROPIC_API_KEY` from `process.env.ANTHROPIC_API_KEY` only — never log or return it
- Return `{ lines: LyricLine[] }` on 200, `{ error: string }` on 500
- Cache check: if `bustCache` is false, check localStorage key `lyrics_<songId>_<datasetId>` first (this is client-side; server just ignores `bustCache: false` — caching is handled by the client)

### Verify

```bash
npm run dev &
sleep 5
curl -s -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"songId":"bohemian-rhapsody","datasetId":"ikea-manuals"}' \
  | python3 -m json.tool | head -50
```

Run 3 times. All must return valid syllable-matched JSON.

### PR description must include

- Sample curl output
- Confirmation that ANTHROPIC_API_KEY does not appear in any response or log

---

## Agent D — Timing Integration

**Branch:** `agent/D-timing-integration`
**Status:** BLOCKED — start only after Agent B's PR merges
**Depends on:** Agent B
**Estimated time:** 1–2 hours

### Your job

Replace the fake proportional word-timing in the karaoke screen with real timestamps.

### What to change

`app/ui/v1/KaraokeScreen.tsx` — timing logic only:

```typescript
// OLD: fake proportional timing
const wordStartMs = (cumSylsBeforeWord / totalSyls) * lineDuration;

// NEW: real timestamps from Agent B's output
// Load data/lrc/<songId>-words.json
// Map each generated word to its { startMs, endMs }
// highlightedWordIndex = words.findIndex(w => currentMs >= w.startMs && currentMs < w.endMs)
```

Do not change any visual design — only the timing source.
The file ownership table says you may touch `app/ui/v1/` for this one purpose.

### Verify

Load bohemian-rhapsody. At `currentMs = 4210`, "Is" must be highlighted.
At `currentMs = 4680`, "real" must be highlighted.
These timestamps come from Agent B's output file — use them exactly.

---

## Agent UI — New UI Implementation (future)

**Branch:** `ui/v2`
**Status:** DO NOT START — wait for A + B + C + D to all merge

### Your job

Replace `app/ui/v1/` entirely. Do not look at it for inspiration.

Read `docs/UX.md` for the full interaction spec.
Read `app/types.ts` for the TypeScript interfaces your components must accept.
Use v0.dev (https://v0.dev) to generate complete screen components from the UX.md descriptions.
Wire them to the real `/api/generate` route and the word-timing data from Agent B.

Three screens to implement: Picker, Generating, Karaoke.
