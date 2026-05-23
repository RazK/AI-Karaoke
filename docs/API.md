# AI Karaoke — API Documentation

## v1 API Overview

v1 has a single server-side API route. All other data (song catalog, datasets, LRC timing) is served as static files bundled with the app.

---

## `POST /api/generate`

Generate AI-rewritten lyrics for a song × dataset combo. This is the only route that runs server-side — it exists solely to keep `ANTHROPIC_API_KEY` off the client.

**Request body**
```json
{
  "songId": "bohemian-rhapsody",
  "datasetId": "ikea-manuals",
  "bustCache": false
}
```

Set `bustCache: true` when the host taps Regenerate — forces a new Claude call even if a cached result exists in localStorage.

**Response `200`**
```json
{
  "lines": [
    {
      "startMs": 4200,
      "original": [["Is"], ["this"], ["the"], ["real"], ["life"]],
      "generated": [["Fix"], ["the"], ["shelf"], ["right"], ["now"]]
    },
    {
      "startMs": 2550,
      "original": [["Is"], ["this"], ["just"], ["fan", "ta", "sy"]],
      "generated": [["Check"], ["the"], ["di", "a", "gram"], ["now"]]
    }
  ]
}
```

### Lyric line format

Each line has three fields:

| Field | Type | Meaning |
|-------|------|---------|
| `startMs` | number | Line start time from the LRC file |
| `original` | `string[][]` | Original words; each word is an array of **syllable strings** |
| `generated` | `string[][]` | Rewritten words; same structure as `original` |

- **One syllable:** `["Fix"]` — one grid column.
- **Multiple syllables:** `["fan", "ta", "sy"]` — three columns; UI may join with `•` for display.
- **Word count** may differ between `original` and `generated`; **total syllable count** must match.
- **Syllable count** for a line = sum of `word.length` over all words (no separate `syllableCount` field).
- **Line order** matches the LRC file (no `lineIndex` field).

The server builds `original` from the LRC and merges it with Claude's `generated` output before returning to the client.

`startMs` is milliseconds from song start (from the LRC file). The client uses this in the RAF loop to highlight the correct line.

**Response `500`**
```json
{ "error": "Generation failed after 3 attempts — syllable counts could not be matched." }
```

**Server behavior**
1. Load `data/lrc/<songId>.json` — split each line's `text` into words and compute syllable counts at runtime (not pre-stored in the file)
2. Load dataset corpus from `data/datasets/<datasetId>.txt`
3. Build prompt and call Claude API (see Prompt Strategy below)
4. Validate syllable counts on every returned line:
   - **Any mismatch** (even 1 syllable off): reject and retry. There is no tolerance.
   - Validation: `syllableCount(original) === syllableCount(generated)` where `syllableCount(line) = sum(word.length for word in line)`.
5. After 3 failures: return 500
6. On success: return the validated lines array

The client caches the response in localStorage under `lyrics_<songId>_<datasetId>`.

---

## Static Data Endpoints

Served as static files — no API route needed.

| File | Contents |
|---|---|
| `/data/songs.json` | `[{ id, title, artist, youtubeId, durationSeconds, lineCount }]` |
| `/data/datasets.json` | `[{ id, label, description }]` |
| `/data/lrc/<id>.json` | `{ id, trackName, artistName, durationSeconds, lines: [{ startMs, text }] }` — syllables are computed at runtime, not stored |

---

## Claude API Prompt Strategy

### Constraints

1. **Syllable count — absolute hard rule.** Total syllables on `generated` must equal total syllables on `original` for every line (zero tolerance). Count = sum of syllable-array lengths per word. Word boundaries may differ; totals may not.
2. **Corpus rewrite — not fill-in-the-blank.** Each generated line must be a **new sentence built from the corpus**, not the original lyric with one or two words swapped. The syllable total comes from the original; the words and phrasing come from the dataset. If a generated line shares most of its words or structure with the original, rewrite it.
3. **Words from the corpus.** Vocabulary and phrases must be drawn from the injected dataset text. Light modification (pluralization, tense) is OK; inventing unrelated words is not.
4. **Structured JSON output.** Each word is a JSON array of syllable strings. Free-form text is rejected and triggers a retry.
5. **Rhyme preservation — soft.** Preserve end-rhymes where possible, never at the cost of rules 1–2.

### Claude response (per batch)

Claude returns **only the generated side** — the server attaches `startMs` and `original` from the LRC:

```json
[
  { "generated": [["Fix"], ["the"], ["shelf"], ["right"], ["now"]] },
  { "generated": [["Check"], ["the"], ["di", "a", "gram"], ["now"]] }
]
```

Array order matches the batched LRC lines.

### Prompt Skeleton

```
You are rewriting the lyrics to "{title}" by {artist} using only words and
phrases from the provided text corpus.

RULES — read all before writing anything:
1. Every generated line MUST have EXACTLY the same syllable count as the original.
   Count syllables as the length of each word's syllable array; line total = sum of those lengths.
2. Write NEW lines from the corpus — do NOT copy the original sentence and swap a word or two.
   BAD (fill-in-the-blank): original "Is this just fantasy?" → "Is this just panel A?"
   GOOD (corpus rewrite):  original "Is this just fantasy?" → "Check the diagram now"
   Both match syllables; the good line reads like the dataset, not like edited song lyrics.
3. Words and phrases must come from the corpus below. Light edits OK; unrelated invention is not.
4. Preserve end-rhymes where possible, but NEVER at the cost of rules 1–2.
5. Return ONLY a JSON array. No commentary, no markdown, no code fences.

SYLLABLE VERIFICATION EXAMPLE:
  original: "No escape from reality" → [["No"], ["es", "cape"], ["from"], ["re", "al", "i", "ty"]]  (8)
  generated MUST total 8 — corpus-style rewrite, e.g.:
  [["In", "sert"], ["screw"], ["type"], ["A"], ["care", "ful", "ly"]]  → 2+1+1+1+3 = 8 ✓
  BAD: [["No"], ["es", "cape"], ["from"], ["re", "al", "i", "ty"]] with one word changed ✗
  BAD: an extra word that makes the sum 9 ✗

Output format (generated only — one object per line in the batch):
[
  { "generated": [["Fix"], ["the"], ["shelf"], ["right"], ["now"]] },
  ...
]

Each word MUST be a JSON array of syllable strings, even single-syllable words: ["Fix"] not "Fix".

--- ORIGINAL LYRICS WITH SYLLABLE COUNTS ---
{annotatedLyrics}

--- CORPUS ---
{datasetText}
```

### Model

`claude-sonnet-4-5`. Syllable constraint compliance requires this capability level.

---

## v2 API Additions

When phones join in v2, the following routes are added:

| Route | Purpose |
|---|---|
| `POST /api/rooms` | Create a room; returns `{ roomCode }` |
| `POST /api/rooms/:code/join` | Guest joins with optional nickname |
| `GET /api/rooms/:code` | Fetch current room state (for reconnection) |
| `POST /api/rooms/:code/start-voting` | Host starts 30s voting round |
| `POST /api/rooms/:code/end-voting` | Host ends voting early |
| `POST /api/rooms/:code/votes/songs` | Toggle guest song vote |
| `POST /api/rooms/:code/votes/datasets` | Toggle guest dataset vote |
| `POST /api/rooms/:code/start-song` | Record `songStartedAt` for guest sync |
| `POST /api/rooms/:code/end-song` | Transition room back to vote feed |

All v2 host-only routes authenticate by checking `guestId` against `rooms.host_guest_id`. Supabase Realtime delivers state transitions to all connected clients.

The `/api/generate` route carries forward unchanged — it accepts an additional `roomCode` parameter in v2 to write the result to Supabase instead of returning it for localStorage.
