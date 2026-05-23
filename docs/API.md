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
      "lineIndex": 0,
      "startMs": 4200,
      "syllableCount": 5,
      "original":  [{ "word": "Is",  "syllables": 1 }, { "word": "this", "syllables": 1 }, { "word": "the",  "syllables": 1 }, { "word": "real", "syllables": 1 }, { "word": "life", "syllables": 1 }],
      "generated": [{ "word": "Fix",  "syllables": 1 }, { "word": "the",  "syllables": 1 }, { "word": "shelf","syllables": 1 }, { "word": "right","syllables": 1 }, { "word": "now",  "syllables": 1 }]
    }
  ]
}
```

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
   - Validation: `sum(generated[i].syllables) === line.syllableCount` for every line `i`.
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

1. **Syllable count — absolute hard rule.** `sum(generated[i].syllables)` must equal `syllableCount` for every line, with zero tolerance. If a word from the corpus is too long, split or replace it. Never add or drop words to fix a count — rewrite the whole line instead.
2. **Words from the corpus.** The dataset text is injected; the model borrows from it rather than inventing freely.
3. **Structured JSON output.** Free-form text is rejected and triggers a retry.
4. **Rhyme preservation — soft.** Preserve end-rhymes where possible, never at the cost of rule 1.

### Prompt Skeleton

```
You are rewriting the lyrics to "{title}" by {artist} using only words and
phrases from the provided text corpus.

RULES — read all before writing anything:
1. Every generated line MUST have EXACTLY the same syllable count as the original.
   Before writing each line: count the original syllables, then verify your
   generated words sum to the same number. If they don't match, rewrite.
2. Words must be drawn from the corpus. You may combine or lightly modify them.
3. Preserve end-rhymes where possible, but NEVER at the cost of rule 1.
4. Return ONLY a JSON array. No commentary, no markdown, no code fences.

SYLLABLE VERIFICATION EXAMPLE:
  original:  [{"word":"No","syllables":1},{"word":"es-cape","syllables":2},
               {"word":"from","syllables":1},{"word":"re-al-i-ty","syllables":4}]
  total = 1+2+1+4 = 8
  generated MUST also sum to 8 — e.g.:
  [{"word":"In-sert","syllables":2},{"word":"screw","syllables":1},
   {"word":"type","syllables":1},{"word":"A","syllables":1},
   {"word":"care-ful-ly","syllables":3}]  → 2+1+1+1+3 = 8 ✓
  NOT: add an extra word like "here" that makes the sum 9 ✗

Output format:
[
  {
    "lineIndex": 0,
    "syllableCount": 5,
    "original":  [{ "word": "Is",  "syllables": 1 }, ...],
    "generated": [{ "word": "Fix", "syllables": 1 }, ...]
  }
]

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
