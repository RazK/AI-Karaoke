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
- Push to `main` directly (open a PR instead)
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
mkdir -p scripts/output scripts/prompt_versions logs
pip install anthropic pyphen
printf "anthropic\npyphen\n" > scripts/requirements.txt
```

### Data you will work with

**LRC file format** (`data/lrc/<songId>.json`):
```json
{
  "id": "bohemian-rhapsody",
  "trackName": "Bohemian Rhapsody",
  "artistName": "Queen",
  "durationSeconds": 354,
  "lines": [
    { "startMs": 0,    "text": "Is this the real life?" },
    { "startMs": 2550, "text": "Is this just fantasy?" }
  ]
}
```
Each line has `startMs` (milliseconds from song start) and `text` (plain string — no pre-split words, no syllable counts). You split and count yourself.

**Dataset corpus files** (`data/datasets/<datasetId>.txt`): plain text files already exist.
Load directly — do NOT hardcode corpus text. Example:
```python
corpus = Path(f"data/datasets/{dataset_id}.txt").read_text()
```

Available dataset IDs: `ikea-manuals`, `yelp-reviews-1star`, `craigslist-ads`, `horoscopes`, `legal-disclaimers`

### Syllable counting — use this everywhere

```python
import pyphen, re

_dic = pyphen.Pyphen(lang='en_US')

def count_syllables(word: str) -> int:
    clean = re.sub(r"[^a-zA-Z']", '', word).lower()
    if not clean:
        return 1
    positions = _dic.positions(clean)
    return len(positions) + 1 if positions else 1
```

Use this for BOTH annotating the original lyrics AND validating the generated output.

### Build `scripts/generate.py`

```bash
python scripts/generate.py --song bohemian-rhapsody --dataset ikea-manuals
```

Complete working skeleton — fill in the prompt, wire up the rest:

```python
#!/usr/bin/env python3
import argparse, json, os, re, sys
from pathlib import Path
import pyphen
import anthropic

_dic = pyphen.Pyphen(lang='en_US')

def count_syllables(word: str) -> int:
    clean = re.sub(r"[^a-zA-Z']", '', word).lower()
    if not clean:
        return 1
    positions = _dic.positions(clean)
    return len(positions) + 1 if positions else 1

def load_lrc(song_id: str) -> list[dict]:
    data = json.loads(Path(f"data/lrc/{song_id}.json").read_text())
    annotated = []
    for i, line in enumerate(data["lines"]):
        words = line["text"].split()
        word_objs = [{"word": w, "syllables": count_syllables(w)} for w in words]
        syllable_count = sum(w["syllables"] for w in word_objs)
        annotated.append({
            "lineIndex": i,
            "startMs": line["startMs"],
            "syllableCount": syllable_count,
            "original": word_objs,
        })
    return annotated

def validate_lines(lines: list) -> list[str]:
    errors = []
    for line in lines:
        orig_sum = sum(w["syllables"] for w in line["original"])
        gen_sum  = sum(w["syllables"] for w in line["generated"])
        if orig_sum != gen_sum:
            errors.append(
                f"Line {line['lineIndex']}: original={orig_sum}, generated={gen_sum} — MISMATCH"
            )
    return errors

def call_claude(prompt: str) -> list:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and Path(".env.local").exists():
        for line in Path(".env.local").read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1]
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fences if model adds them despite instructions
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return json.loads(text)

def build_prompt(annotated_lines: list, corpus: str) -> str:
    return f"""You are rewriting song lyrics using text from a provided corpus.

RULES — follow all of them exactly:
1. Every generated line MUST have EXACTLY the same syllable count as the original.
   Count carefully. Before writing each line:
   a. Count the syllables in the original (they are provided for you)
   b. Write your generated words
   c. Count again and verify the sums match
   If they don't match, rewrite the line.
2. Take words and phrases from the provided corpus. Adapt lightly but stay close.
3. Preserve end-rhymes if possible. Never at the cost of rule 1.
4. Return ONLY valid JSON. No commentary, no code fences, no markdown.

SYLLABLE VERIFICATION EXAMPLE:
  original: [{{"word":"No","syllables":1}},{{"word":"es-cape","syllables":2}},
             {{"word":"from","syllables":1}},{{"word":"re-al-i-ty","syllables":4}}]
  sum = 1+2+1+4 = 8
  good generated (sum=8):
  [{{"word":"In-sert","syllables":2}},{{"word":"screw","syllables":1}},
   {{"word":"type","syllables":1}},{{"word":"A","syllables":1}},
   {{"word":"care-ful-ly","syllables":3}}]  → 2+1+1+1+3 = 8 ✓
  bad (sum=9): add "here"(1) → 9 ✗  WRONG, rewrite.

OUTPUT FORMAT — return a JSON array, nothing else:
[
  {{
    "lineIndex": 0,
    "syllableCount": 5,
    "startMs": 0,
    "original":  [{{"word": "Is",  "syllables": 1}}, ...],
    "generated": [{{"word": "Fix", "syllables": 1}}, ...]
  }}
]

--- ORIGINAL LYRICS (annotated with syllable counts) ---
{json.dumps(annotated_lines, indent=2)}

--- CORPUS ---
{corpus}"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--song", required=True)
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()

    log_path = Path("logs/agent-A-status.md")
    log_path.parent.mkdir(exist_ok=True)

    annotated = load_lrc(args.song)
    corpus = Path(f"data/datasets/{args.dataset}.txt").read_text()

    log_path.write_text(f"# Agent A run: {args.song} × {args.dataset}\n\n")
    log_path.open("a").write(f"Loaded {len(annotated)} lines, corpus {len(corpus)} chars\n\n")

    prompt = build_prompt(annotated, corpus)
    errors = ["initial"]
    lines = []

    for attempt in range(3):
        try:
            lines = call_claude(prompt)
            errors = validate_lines(lines)
        except Exception as e:
            errors = [f"Exception: {e}"]

        log_path.open("a").write(f"## Attempt {attempt+1}\nErrors: {errors or 'NONE — PASS'}\n\n")

        if not errors:
            break

        prompt += f"\n\nPREVIOUS ATTEMPT FAILED — fix ONLY these lines, keeping all others:\n" + "\n".join(errors)

    out = Path(f"scripts/output/{args.song}-{args.dataset}.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(lines, indent=2))

    if errors:
        print(f"FAILED after 3 attempts: {errors}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(lines, indent=2))

if __name__ == "__main__":
    main()
```

### Iteration guidance

Run the script. Check `logs/agent-A-status.md` after each run. If syllable matching is failing:
- Try asking for chain-of-thought in a `"scratchpad"` field (then strip from output in `call_claude`)
- Try reducing batch size — pass 10 lines at a time instead of all 54
- Try `claude-opus-4-7` if `claude-sonnet-4-5` keeps failing (higher cost, better compliance)

Keep all prompt versions in `scripts/prompt_versions/v1.txt`, `v2.txt`, etc. with a note on what changed.

### Done when

Run this 5 times:
```bash
python scripts/generate.py --song bohemian-rhapsody --dataset ikea-manuals
```
At least 4 of 5 must produce zero syllable mismatches on first attempt (no retries needed).
Also run once with `--dataset yelp-reviews-1star` to prove it's not tied to one corpus.
Write all results to `scripts/output/` for the PR.

Verification command:
```bash
python3 -c "
import json, sys
data = json.load(open('scripts/output/bohemian-rhapsody-ikea-manuals.json'))
errors = [f'Line {l[\"lineIndex\"]}: {sum(w[\"syllables\"] for w in l[\"original\"])} vs {sum(w[\"syllables\"] for w in l[\"generated\"])}' for l in data if sum(w[\"syllables\"] for w in l['original']) != sum(w['syllables'] for w in l['generated'])]
print('PASS' if not errors else 'FAIL: ' + str(errors))
"
```

### Commit cadence

```bash
git add scripts/ logs/ && git commit -m "agent-A: scaffold generate.py" && git push
git add . && git commit -m "agent-A: prompt v2 — X/5 pass rate" && git push
git add . && git commit -m "agent-A: DONE — 5/5 pass, prompt finalized" && git push
```

### PR description must include

- The final prompt (complete, verbatim — Agent C copies it exactly)
- Pass rate across all 5+ runs
- Sample JSON output for bohemian-rhapsody × ikea-manuals AND × yelp-reviews-1star
- Which model was used and why

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
apt-get install -y ffmpeg 2>/dev/null || true   # required by whisper
pip install openai-whisper yt-dlp
printf "openai-whisper\nyt-dlp\n" > scripts/requirements-B.txt
```

`openai-whisper` requires `ffmpeg` to be installed — without it, transcription will silently fail or crash.
Model weights download on first use (~140MB for `base`). This is normal; it's cached after the first run.

### LRC file format (what you'll read for the fallback)

`data/lrc/bohemian-rhapsody.json`:
```json
{
  "id": "bohemian-rhapsody",
  "lines": [
    { "startMs": 0,    "text": "Is this the real life?" },
    { "startMs": 2550, "text": "Is this just fantasy?" },
    { "startMs": 5170, "text": "Caught in a landslide" }
  ],
  "durationSeconds": 354
}
```

### Song YouTube IDs (from `data/songs.json`)

| Song | youtubeId |
|------|-----------|
| bohemian-rhapsody | `fJ9rUzIMcZQ` |
| never-gonna-give-you-up | `dQw4w9WgXcQ` |
| africa | `FTQbiNvZqaY` |
| someone-like-you | `hLQl3WQQoQ0` |
| dont-stop-believin | `1k8craCGpgs` |

### Build `scripts/align.py`

```bash
# Test network first:
yt-dlp --simulate "https://www.youtube.com/watch?v=fJ9rUzIMcZQ"

# If that works, run for real:
python scripts/align.py --song bohemian-rhapsody
# Produces: data/lrc/bohemian-rhapsody-words.json
```

Complete script:

```python
#!/usr/bin/env python3
import argparse, json, os, re, subprocess, sys
from pathlib import Path

def get_youtube_id(song_id: str) -> str:
    songs = json.loads(Path("data/songs.json").read_text())
    for s in songs:
        if s["id"] == song_id:
            return s["youtubeId"]
    raise ValueError(f"Song not found: {song_id}")

def download_audio(youtube_id: str, song_id: str) -> str | None:
    out_path = f"/tmp/{song_id}.mp3"
    if os.path.exists(out_path):
        print(f"Using cached audio: {out_path}")
        return out_path
    result = subprocess.run([
        "yt-dlp", "-x", "--audio-format", "mp3",
        "--audio-quality", "0", "-o", out_path,
        f"https://www.youtube.com/watch?v={youtube_id}"
    ])
    if result.returncode != 0:
        return None
    return out_path

def transcribe_with_whisper(audio_path: str) -> list[dict]:
    import whisper
    print("Loading Whisper base model...")
    model = whisper.load_model("base")
    print("Transcribing (this takes a few minutes)...")
    result = model.transcribe(audio_path, word_timestamps=True, language="en")
    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({
                "word":    w["word"].strip(),
                "startMs": int(w["start"] * 1000),
                "endMs":   int(w["end"]   * 1000),
            })
    return words

def synthetic_timestamps(song_id: str) -> list[dict]:
    """Fallback: distribute words evenly across each LRC line's time window."""
    data = json.loads(Path(f"data/lrc/{song_id}.json").read_text())
    lines = data["lines"]
    duration_ms = data["durationSeconds"] * 1000
    words = []
    for i, line in enumerate(lines):
        line_start = line["startMs"]
        line_end = lines[i + 1]["startMs"] if i + 1 < len(lines) else duration_ms
        line_words = line["text"].split()
        if not line_words:
            continue
        slot = (line_end - line_start) / len(line_words)
        for j, w in enumerate(line_words):
            words.append({
                "word":    w,
                "startMs": int(line_start + j * slot),
                "endMs":   int(line_start + (j + 1) * slot),
            })
    return words

def spot_check(words: list[dict], song_id: str) -> str:
    lrc = json.loads(Path(f"data/lrc/{song_id}.json").read_text())
    report = ["## Spot-check: first word of each LRC line vs expected startMs\n"]
    report.append("| LRC line | Expected startMs | First whisper word | Whisper startMs | Drift |")
    report.append("|----------|------------------|--------------------|-----------------|-------|")
    for line in lrc["lines"][:10]:
        expected = line["startMs"]
        first_word_text = line["text"].split()[0].lower().strip(",.!?")
        # Find nearest word in whisper output
        match = min(words, key=lambda w: abs(w["startMs"] - expected))
        drift = match["startMs"] - expected
        report.append(f'| "{line["text"][:25]}" | {expected} | "{match["word"]}" | {match["startMs"]} | {drift:+d}ms |')
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--song", required=True)
    args = parser.parse_args()

    log = Path("logs/agent-B-status.md")
    log.parent.mkdir(exist_ok=True)
    log.write_text(f"# Agent B: {args.song}\n\n")

    youtube_id = get_youtube_id(args.song)
    log.open("a").write(f"YouTube ID: {youtube_id}\n")

    audio_path = download_audio(youtube_id, args.song)
    method = "whisper"

    if audio_path:
        log.open("a").write("yt-dlp: SUCCESS\n")
        words = transcribe_with_whisper(audio_path)
    else:
        log.open("a").write("yt-dlp: FAILED — using synthetic timestamps\n")
        words = synthetic_timestamps(args.song)
        method = "synthetic"

    log.open("a").write(f"Method: {method}\nWords extracted: {len(words)}\n\n")
    log.open("a").write(spot_check(words, args.song))

    out = {"songId": args.song, "method": method, "words": words}
    out_path = Path(f"data/lrc/{args.song}-words.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {len(words)} words to {out_path} (method={method})")

if __name__ == "__main__":
    main()
```

### Accuracy notes

- `base` model: fast (~5 min on CPU), ~60% word accuracy, timing within ~200ms — acceptable for v1
- `medium` model: slow (~30-60 min on CPU), ~80% word accuracy, timing within ~50ms
- Start with `base`. Check spot-check table in `logs/agent-B-status.md`. If drift > 500ms consistently, rerun with `medium` (change `load_model("base")` to `load_model("medium")`).
- Synthetic timestamps are a last resort — they give correct word order but fake timing. Document clearly if used.

### Done when

`data/lrc/bohemian-rhapsody-words.json` exists with at least 200 words.

Verification:
```bash
python3 -c "
import json
data = json.load(open('data/lrc/bohemian-rhapsody-words.json'))
words = data['words']
print(f'Total words: {len(words)}')
print(f'Method: {data[\"method\"]}')
print('First 5:', [(w[\"word\"], w[\"startMs\"]) for w in words[:5]])
print('At t=10s:', [w[\"word\"] for w in words if 9000 < w[\"startMs\"] < 11000])
"
```

### Commit cadence

```bash
git add . && git commit -m "agent-B: setup + yt-dlp test" && git push
git add . && git commit -m "agent-B: whisper done, spot-check written" && git push
git add . && git commit -m "agent-B: DONE — words written for bohemian-rhapsody" && git push
```

### PR description must include

- Which method: whisper (base/medium) or synthetic — and why
- Spot-check table from `logs/agent-B-status.md`
- First 20 words of the output JSON
- Total word count

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

### Data the route reads (server-side file reads — not client)

- `data/lrc/<songId>.json` — same format as Agent A uses (see Agent A section for schema)
- `data/datasets/<datasetId>.txt` — plain text corpus

The route must read these files at request time using `fs.readFileSync` or `fs/promises`.
These are static files in the repo, not fetched over HTTP.

### Build `app/api/generate/route.ts`

Use this skeleton — fill in `buildPrompt()` with Agent A's final prompt verbatim:

```typescript
import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import fs from 'fs';
import path from 'path';
import { LyricLine } from '@/app/types';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

function loadLrc(songId: string) {
  const p = path.join(process.cwd(), 'data', 'lrc', `${songId}.json`);
  const data = JSON.parse(fs.readFileSync(p, 'utf8'));
  // Annotate with syllable counts using the same logic as Agent A
  // (copy count_syllables logic or use a JS syllable library)
  return data.lines.map((line: { startMs: number; text: string }, i: number) => ({
    lineIndex: i,
    startMs: line.startMs,
    text: line.text,
    // syllableCount computed here from splitting line.text
  }));
}

function loadCorpus(datasetId: string): string {
  const p = path.join(process.cwd(), 'data', 'datasets', `${datasetId}.txt`);
  return fs.readFileSync(p, 'utf8');
}

function buildPrompt(annotatedLines: object[], corpus: string): string {
  // PASTE AGENT A'S FINAL PROMPT VERBATIM HERE
  // Replace {annotated_lyrics_json} and {corpus_text} with the actual values
  throw new Error('buildPrompt not implemented — paste Agent A prompt here');
}

function validateLines(lines: LyricLine[]): string[] {
  return lines
    .filter(line => {
      const origSum = line.original.reduce((s, w) => s + w.syllables, 0);
      const genSum  = line.generated.reduce((s, w) => s + w.syllables, 0);
      return origSum !== genSum;
    })
    .map(line => {
      const o = line.original.reduce((s, w) => s + w.syllables, 0);
      const g = line.generated.reduce((s, w) => s + w.syllables, 0);
      return `Line ${line.lineIndex}: original=${o}, generated=${g}`;
    });
}

export async function POST(req: NextRequest) {
  try {
    const { songId, datasetId } = await req.json();
    if (!songId || !datasetId) {
      return NextResponse.json({ error: 'songId and datasetId required' }, { status: 400 });
    }

    const annotatedLines = loadLrc(songId);
    const corpus = loadCorpus(datasetId);
    let prompt = buildPrompt(annotatedLines, corpus);
    let lines: LyricLine[] = [];
    let errors: string[] = ['initial'];

    for (let attempt = 0; attempt < 3; attempt++) {
      const msg = await client.messages.create({
        model: 'claude-sonnet-4-5',
        max_tokens: 8192,
        messages: [{ role: 'user', content: prompt }],
      });
      const text = (msg.content[0] as { text: string }).text
        .replace(/^```[a-z]*\n?/, '').replace(/\n?```$/, '');
      lines = JSON.parse(text);
      errors = validateLines(lines);
      if (!errors.length) break;
      prompt += `\n\nPREVIOUS ATTEMPT FAILED. Fix ONLY these lines:\n${errors.join('\n')}`;
    }

    if (errors.length) {
      return NextResponse.json({ error: `Syllable mismatch after 3 attempts: ${errors.join('; ')}` }, { status: 500 });
    }

    return NextResponse.json({ lines });
  } catch (err) {
    console.error('/api/generate error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
```

For syllable counting in TypeScript, install `npm install syllable` and use:
```typescript
import { syllable } from 'syllable';
// syllable('fantasy') === 3
```

### Verify

```bash
npm run dev &
sleep 8
curl -s -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"songId":"bohemian-rhapsody","datasetId":"ikea-manuals"}' \
  | python3 -m json.tool | head -60
```

Run 3 times. All must return `{ lines: [...] }` with zero syllable mismatches.

Validate the response:
```bash
curl -s -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"songId":"bohemian-rhapsody","datasetId":"ikea-manuals"}' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
lines = data.get('lines', [])
errors = [f'Line {l[\"lineIndex\"]}' for l in lines if sum(w['syllables'] for w in l['original']) != sum(w['syllables'] for w in l['generated'])]
print('PASS' if not errors else 'FAIL: ' + str(errors))
print(f'{len(lines)} lines returned')
"
```

### PR description must include

- Sample curl output (first 20 lines of JSON)
- Verification script output showing PASS
- Confirmation ANTHROPIC_API_KEY does not appear in any response or log

---

## Agent D — Timing Integration

**Branch:** `agent/D-timing-integration`
**Status:** BLOCKED — start only after Agent B's PR merges
**Depends on:** Agent B
**Estimated time:** 1–2 hours

### Your job

Replace the fake proportional word-timing in the karaoke screen with real timestamps.

### What to change

The active karaoke component is **`app/components/KaraokeScreen.tsx`** — this is what `app/page.tsx` imports and what runs in the browser.

The component currently uses `MOCK_LYRICS` hardcoded at the top of the file and fake proportional timing. You need to:

1. **Wire up real lyrics from `/api/generate`** — the `GeneratingScreen` already calls `onDone(lyrics)` which passes `LyricLine[]` to `KaraokeScreen` via `app/page.tsx`. The `lyrics` prop is already there; just remove the `MOCK_LYRICS` fallback and use `props.lyrics` directly.

2. **Replace fake timing with Agent B's word timestamps** — load `data/lrc/<songId>-words.json` at component mount and use those timestamps to drive `highlightedWordIndex`:

```typescript
// Add to KaraokeScreen, after component mounts:
const [wordTimings, setWordTimings] = useState<{word: string; startMs: number; endMs: number}[]>([]);

useEffect(() => {
  fetch(`/data/lrc/${song.id}-words.json`)
    .then(r => r.json())
    .then(data => setWordTimings(data.words))
    .catch(() => {}); // graceful fallback — component works without it
}, [song.id]);

// Then in the RAF/interval loop, replace proportional highlighting with:
// const activeWord = wordTimings.find(w => currentMs >= w.startMs && currentMs < w.endMs);
// Use activeWord?.word to match against the generated word currently being rendered
```

Do not change any visual design — only remove MOCK_LYRICS and fix the timing source.

### How matching works

The generated words are different text from the original, but they map 1-to-1 by syllable count. Agent B's word timestamps are from the ORIGINAL song audio. So you match by position: the Nth generated word is highlighted when the Nth original word's timestamp is active.

Track a running word index across all lines:
```typescript
// Build a flat array of original word timestamps across all lines
// wordsFlat[i] = { startMs, endMs } from Agent B's output, in order
// Then: highlightedFlatIndex = wordsFlat.findIndex(w => currentMs >= w.startMs && currentMs < w.endMs)
// Map flatIndex back to (lineIndex, wordIndex) for rendering
```

### Verify

```bash
npm run dev
# Open http://localhost:3000
# Pick bohemian-rhapsody + any dataset
# Wait for generation, then on karaoke screen:
# - Check browser console for any errors
# - Verify words highlight as time advances
# - At t=0ms, first word "Is"/"Fix" must be highlighted
```

Unit-level check (paste into browser console on karaoke screen):
```javascript
// Should log the word active at t=4210ms
console.log(window.__wordTimings?.find(w => 4210 >= w.startMs && 4210 < w.endMs))
```
(Add `window.__wordTimings = wordTimings` in the component for this to work during dev.)

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
