# AI Karaoke — API Documentation

## Conventions

- All REST endpoints are Next.js API routes under `/api/`
- All request and response bodies are JSON
- Error shape: `{ "error": "human-readable message" }`
- Room codes are 6 uppercase alphanumeric characters (e.g. `XKCD42`)
- Guest IDs are UUIDs, generated client-side and persisted in localStorage
- Host authentication uses a 4-digit PIN passed in the request body

---

## REST Endpoints

### `POST /api/rooms`

Create a new room. The caller becomes the host.

**Request body**
```json
{ "hostGuestId": "uuid" }
```

**Response `201`**
```json
{
  "roomCode": "XKCD42",
  "hostPin": "4829"
}
```

The host stores `hostPin` in localStorage as `hostPin_XKCD42`. All host-only actions require this PIN. Any device that enters the correct PIN gains host controls.

---

### `POST /api/rooms/:code/join`

Join a room as a guest. Guests are anonymous.

**Request body**
```json
{ "guestId": "uuid" }
```

**Validation:** Room must exist with fewer than 20 guests.

**Response `200`**
```json
{
  "roomCode": "XKCD42",
  "state": "room",
  "guestCount": 3
}
```

`state` tells the client which screen to show immediately.

---

### `GET /api/rooms/:code`

Fetch full current room state. Used on reconnect to restore client state without waiting for a Realtime event.

**Response `200`**
```json
{
  "roomCode": "XKCD42",
  "state": "karaoke",
  "guestCount": 7,
  "currentSong": { "id": "bohemian-rhapsody", "title": "Bohemian Rhapsody", "artist": "Queen", "youtubeId": "fJ9rUzIMcZQ" },
  "currentDataset": { "id": "ikea-manuals", "label": "IKEA Manuals" },
  "songStartedAt": 1716000000000
}
```

---

### `GET /api/songs`

Return the song catalog. Optionally filter with `?q=`.

**Query params:** `q` — case-insensitive substring match against title and artist.

**Response `200`**
```json
{
  "songs": [
    {
      "id": "bohemian-rhapsody",
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "youtubeId": "fJ9rUzIMcZQ",
      "durationSeconds": 354,
      "lineCount": 62
    }
  ]
}
```

---

### `GET /api/datasets`

Return the dataset catalog. Optionally filter with `?q=`.

**Response `200`**
```json
{
  "datasets": [
    {
      "id": "ikea-manuals",
      "label": "IKEA Manuals",
      "description": "Step-by-step furniture assembly instructions"
    }
  ]
}
```

---

### `POST /api/rooms/:code/start-voting`

Start a 30-second timed voting round. Host only.

**Request body**
```json
{ "hostPin": "4829" }
```

**Response `202`**
```json
{ "votingEndsAt": 1716000030000 }
```

Transitions room from `room` → `voting`. When the timer expires, the server automatically picks winners and calls `/api/rooms/:code/generate`.

---

### `POST /api/rooms/:code/end-voting`

End the voting round early and proceed with current leaders. Host only.

**Request body**
```json
{ "hostPin": "4829" }
```

**Response `202`**
```json
{ "songId": "bohemian-rhapsody", "datasetId": "ikea-manuals" }
```

---

### `POST /api/rooms/:code/votes/songs`

Toggle the calling guest's song vote. Available in both `room` and `voting` states.

**Request body**
```json
{ "guestId": "uuid", "songId": "bohemian-rhapsody" }
```

**Response `200`**
```json
{ "songId": "bohemian-rhapsody", "votes": 6, "voted": true }
```

`voted` reflects the guest's vote state after the toggle.

---

### `POST /api/rooms/:code/votes/datasets`

Toggle the calling guest's dataset vote.

**Request body**
```json
{ "guestId": "uuid", "datasetId": "ikea-manuals" }
```

**Response `200`**
```json
{ "datasetId": "ikea-manuals", "votes": 4, "voted": true }
```

---

### `POST /api/rooms/:code/generate`

Trigger AI lyric generation. Host only.

**Request body**
```json
{
  "songId": "bohemian-rhapsody",
  "datasetId": "ikea-manuals",
  "hostPin": "4829",
  "bustCache": false
}
```

Set `bustCache: true` when regenerating — forces a new Claude API call even if a cached result exists.

**Response `202`**
```json
{ "jobId": "uuid" }
```

Generation is async. Progress and result are delivered via Supabase Realtime. See Events section.

**Server behavior:**
1. Check `lyrics` table for `(songId, datasetId)` — return cached result if `bustCache` is false
2. Otherwise: call Claude API with syllable-annotated lyrics + dataset corpus
3. Validate syllable counts; retry up to 2 times on mismatch > 1 syllable
4. After 3 failures: update room state to `error`, surface to host
5. On success: upsert to `lyrics` table, update `rooms.state = 'karaoke'`

---

### `POST /api/rooms/:code/start-song`

Record the song start timestamp. Called by the host client when YouTube fires `onStateChange(PLAYING)`.

**Request body**
```json
{ "hostPin": "4829", "songStartedAt": 1716000000000 }
```

**Response `200`**
```json
{ "songStartedAt": 1716000000000 }
```

Stores `song_started_at` in the `rooms` row. Supabase Realtime broadcasts to all clients, who start their timing loops.

---

### `POST /api/rooms/:code/end-song`

Transition room from `karaoke` → `room` (back to vote feed). Host only.

**Request body**
```json
{ "hostPin": "4829" }
```

**Response `200`**
```json
{ "state": "room" }
```

---

## Supabase Realtime Events

Clients subscribe to their room row in Supabase using `supabase.channel('room:XKCD42')`. All state transitions are delivered as Postgres row-level changes.

### Room state changes

Fired whenever `rooms.state` or related columns change. Clients read the updated row and switch screens.

```
rooms.state = 'voting'     → show Voting Round screen; votingEndsAt is set
rooms.state = 'generating' → show Generating screen
rooms.state = 'karaoke'    → show Karaoke screen; songStartedAt is set
rooms.state = 'room'       → show Room screen (vote feed)
```

### Vote tally updates

Clients subscribe to `votes_songs` and `votes_datasets` filtered by `room_code`. On any insert/update/delete, the client re-queries the tally and re-renders the feed.

### Generation progress

Emitted by the server during Claude API call via a Supabase Realtime broadcast (not a row change):

```json
{
  "event": "generation:progress",
  "percent": 40
}
```

Clients use this to animate the progress bar. The bar fills to ~90% and completes when `rooms.state` changes to `karaoke`.

---

## Claude API Prompt Strategy

The prompt is the core of the product. Full spec below.

### Constraints (enforced at prompt level)

1. **Syllable count is a hard constraint.** Each line is provided with syllable annotations. The model must return the same count.
2. **Words come from the dataset corpus.** The dataset text is injected; the model borrows from it rather than inventing freely.
3. **Output is structured JSON.** Free-form text is rejected server-side.
4. **Rhyme scheme is a soft constraint.** Preserve end-rhymes where possible, never at the cost of syllable count.

### Prompt Skeleton

```
You are rewriting the lyrics to "{title}" by {artist} using only words and
phrases from the provided text corpus.

Rules:
1. Every line must have EXACTLY the same number of syllables as the original.
2. Words must be drawn from the corpus. You may combine or lightly modify them.
3. Preserve end-rhymes where possible, but never at the cost of rule 1.
4. Return ONLY a JSON array. No commentary, no markdown.

Output format:
[
  {
    "lineIndex": 0,
    "syllableCount": 5,
    "original":   [{ "word": "Is",   "syllables": 1 }, { "word": "this", "syllables": 1 }, ...],
    "generated":  [{ "word": "Fix",  "syllables": 1 }, { "word": "the",  "syllables": 1 }, ...]
  }
]

--- ORIGINAL LYRICS WITH SYLLABLE COUNTS ---
{annotatedLyrics}

--- CORPUS ---
{datasetText}
```

### Server-Side Validation

After each Claude response:

1. For each line: count syllables in `generated` entries using CMU Pronouncing Dictionary (fallback: heuristic splitter)
2. If any line is off by exactly 1 syllable: accept and log
3. If any line is off by more than 1 syllable: retry the full generation (max 2 retries)
4. After 3 total failures: return error to host

### Model

Use `claude-sonnet-4` (`claude-sonnet-4-20250514`). Syllable constraint compliance requires this model.
