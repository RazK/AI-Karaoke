# AI Karaoke — Software Design Document

## 1. System Overview

AI Karaoke v1 is a web app that runs on one device — a laptop or TV. The host picks a song and a dataset, Claude rewrites the lyrics syllable-for-syllable, and the group sings along to the music playing on screen.

---

## 2. Architecture

### 2.1 Diagram

```
Browser (host laptop / TV)
        │
        │ HTTPS
        ▼
  ┌─────────────┐       ┌──────────────┐
  │  Next.js    │──────▶│  Claude API  │
  │  (Vercel)   │       │  (via /api/  │
  │             │       │   generate)  │
  └──────┬──────┘       └──────────────┘
         │
    ┌────┴────────────────┐
    │                     │
YouTube IFrame         localStorage
(audio + sync)        (lyrics cache)
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|---|---|
| **Next.js (App Router)** | All UI screens and the `/api/generate` route |
| **`/api/generate` route** | Vercel serverless function — Claude API proxy; `ANTHROPIC_API_KEY` stays server-side |
| **YouTube IFrame API** | Audio playback; `getCurrentTime()` drives karaoke sync |
| **LRCLib + `lrc-kit`** | Per-line LRC timing data parsed from static JSON files |
| **localStorage** | Lyrics cache for the current session |

### 2.3 Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js 14+ (App Router) | File-based routing, server components, Vercel-native |
| Styling | Tailwind CSS | Utility-first, fast iteration |
| AI | Claude API (`claude-sonnet-4`) | Best instruction-following for structured JSON output |
| Audio | YouTube IFrame API | Free; YouTube handles licensing and delivery |
| Lyric timing | LRCLib + `lrc-kit` | Free, keyless, 3M+ songs, millisecond-accurate line timestamps |
| Hosting | Vercel | Zero-ops, auto-deploys `main`, PR preview URLs |
| State | React + localStorage | Session-scoped lyrics cache |

### 2.4 Key Architectural Decisions

**Single serverless route for Claude.**
All app state lives in the browser. The only server-side code is `/api/generate` — a thin proxy that holds the `ANTHROPIC_API_KEY` and calls Claude. Everything else (song catalog, LRC timing, cached lyrics) is client-side.

**localStorage lyrics cache.**
Generated lyrics for a song × dataset combo are cached in localStorage under the key `lyrics_<songId>_<datasetId>`. The same combo within a session returns instantly. Bust the cache by passing `bustCache: true` to `/api/generate`.

**Frame-accurate sync via `getCurrentTime()`.**
When the host taps Play, the YouTube player starts and `songStartedAt = Date.now()` is recorded in React state. The karaoke RAF loop uses `player.getCurrentTime() * 1000` — the player's own clock — for frame-accurate line highlighting. This is drift-free regardless of buffering or network latency.

**Static catalog data.**
Songs and datasets are static JSON files bundled with the app. No database reads needed to browse the catalog.

---

## 3. Data

### 3.1 Static Catalog Files

```
data/songs.json      — [{ id, title, artist, youtubeId, durationSeconds, lineCount }]
data/datasets.json   — [{ id, label, description }]
data/lrc/<id>.json   — { lines: [{ startMs, text, syllables: [{ word, count }] }] }
```

`youtubeId` is the 11-character YouTube video ID. The karaoke screen loads the player with this ID.

### 3.2 localStorage Schema

```
lyrics_<songId>_<datasetId>  →  JSON string of the lines array (same shape as /api/generate response)
```

Cleared only when the browser storage is cleared. Survives page refreshes within a session.

---

## 4. Component Design

### 4.1 App Flow

```
Picker screen
  └─ Host selects song card + dataset card
  └─ Host taps Generate
        └─ Check localStorage cache
              ├─ Cache hit → skip to Karaoke screen
              └─ Cache miss → call /api/generate
                    └─ Progress screen (spinner + flavor text)
                    └─ On success → Karaoke screen
                    └─ On failure → error toast, stay on Picker

Karaoke screen
  └─ Host taps Play
        └─ player.playVideo()
        └─ YouTube fires onStateChange(PLAYING)
        └─ songStartedAt = Date.now()
        └─ RAF loop starts: currentLine = lrc.findLineAt(player.getCurrentTime() * 1000)
  └─ Host taps Regenerate → back to Progress screen (bustCache: true)
  └─ Host taps New Combo → back to Picker screen
```

### 4.2 Lyric Generation

```
POST /api/generate receives { songId, datasetId, bustCache }
  1. Load syllable-annotated lyrics from data/lrc/<songId>.json
  2. Load dataset corpus text
  3. Build prompt (see API.md)
  4. Call Claude API, expect JSON array
  5. Validate each line's syllable count
     - Off by 1: accept, log
     - Off by > 1: retry (max 2 retries)
     - 3 failures: return 500 with error message
  6. Return validated lines array
```

Client receives the lines array, writes it to localStorage, and navigates to the Karaoke screen.

### 4.3 Karaoke Timing

```javascript
// Called on every animation frame during playback
function onFrame() {
  const positionMs = player.getCurrentTime() * 1000
  const line = lrc.findLineAt(positionMs)
  setCurrentLineIndex(line.index)
  if (positionMs >= song.durationMs) endSong()
  requestAnimationFrame(onFrame)
}
```

`player.getCurrentTime()` is YouTube's own playback clock — it accounts for buffering, seeks, and any latency. The display is always in sync with what the host hears.

### 4.4 Syllable Grid

Each lyric line renders as a CSS grid:

```css
grid-template-columns: repeat(N, 1fr)  /* N = total syllable count */
```

Each word's `grid-column` is `startSyllable / span syllableCount`. Both rows (generated on top, original below) share the same grid, so syllables align vertically.

If the grid is too wide for the screen, both rows split at the same syllable-column boundary — they always wrap together.

---

## 5. Deployment

### 5.1 Vercel

- Auto-deploys on push to `main`
- PR branches get preview URLs
- Only `/api/generate` runs as a serverless function; everything else is static

### 5.2 Environment Variables

```
ANTHROPIC_API_KEY=    # Server-side only — never exposed to the browser
```

No other environment variables needed in v1.

### 5.3 npm Packages

| Package | Purpose |
|---|---|
| `@anthropic-ai/sdk` | Claude API client (server-side only) |
| `lrc-kit` | Parse LRC timing data |
| `tailwindcss` | Styling |

---

## 6. v2 Architecture Additions

When phones join in v2, the following are added:

- **Supabase** — real-time DB replaces localStorage for shared state (rooms, votes, lyrics cache)
- **Room system** — 6-character room code, QR code, guest join flow
- **Supabase Realtime** — state transitions broadcast to all clients (TV + phones)
- **Guest identity** — UUID in localStorage; optional nickname at join
- **Voting** — `votes_songs` and `votes_datasets` tables; 30-second timed rounds
- **Companion view** — guest phones show lyrics synced via `Date.now() - songStartedAt`

The v1 `/api/generate` route carries forward unchanged into v2.
