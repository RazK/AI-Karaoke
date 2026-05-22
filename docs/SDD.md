# AI Karaoke — Software Design Document

## 1. System Overview

AI Karaoke is a web app where one host (laptop/TV) creates a room and up to 20 guests join via phone. Guests vote on a song + dataset combo; the app calls Claude to rewrite the lyrics syllable-for-syllable; the group sings along to the song playing inside the app on the host screen.

No native app. No separate audio device needed — music plays via an embedded YouTube player on the karaoke screen.

---

## 2. Architecture

### 2.1 High-Level Diagram

```
Phones (guests)              Laptop / TV (host)
     │                              │
     └──────────┬───────────────────┘
                │ HTTPS + Supabase Realtime
                ▼
         ┌─────────────────┐
         │  Next.js App    │  ← hosted on Vercel (serverless)
         │  (App Router)   │
         └────────┬────────┘
                  │
       ┌──────────┴──────────┐
       │                     │
  ┌────▼────┐         ┌──────▼──────┐
  │Supabase │         │  Claude API │
  │DB + RT  │         │ (/api/gen.) │
  └─────────┘         └─────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|---|---|
| **Next.js (App Router)** | All UI screens, server components, API routes |
| **Supabase** | Persistent state (rooms, votes, lyrics), real-time subscriptions |
| **`/api/generate` route** | Server-side Claude API proxy — key never reaches the client |
| **YouTube IFrame API** | In-app music playback on the host/TV screen |
| **LRCLib** | Free per-line LRC timing data for karaoke sync |
| **Vercel** | Hosting, serverless function execution, auto-deploy from `main` |

### 2.3 Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js 14+ (App Router) | Server components, file-based routing, Vercel-native |
| Styling | Tailwind CSS | Utility-first, fast iteration |
| Real-time | Supabase Realtime | Replaces Socket.io + Redis; single managed service |
| Database | Supabase (PostgreSQL) | Same service as real-time; free tier sufficient for v1 |
| AI | Claude API (`claude-sonnet-4`) | Best instruction-following for structured JSON output |
| Audio | YouTube IFrame API | Free, no licensing burden, no audio file storage needed |
| Lyric timing | LRCLib + `lrc-kit` (npm) | Free, no API key, 3M+ songs, millisecond-accurate line timestamps |
| Deployment | Vercel | Zero-ops, auto-deploys `main`, PR preview URLs |

### 2.4 Key Architectural Decisions

**No Redis, no Socket.io, no separate Express server.**
Supabase handles real-time subscriptions and persistent state. This eliminates all infrastructure management — no servers, no queues, no pub/sub setup.

**Client-side timing loop.**
The host presses "Let's Sing", which simultaneously starts the YouTube player and records `songStartedAt` in the database. Every client independently computes the current lyric line using `lrc.findLineAt(Date.now() - songStartedAt)` in a `requestAnimationFrame` loop. No server clock. No per-line events. Latency differences between clients cause < 100ms drift, which is imperceptible.

**Claude API proxied through a serverless route.**
`ANTHROPIC_API_KEY` lives only in Vercel environment variables. The client never calls Claude directly. `/api/generate` is the only entry point to the AI.

**Host PIN instead of JWT.**
The host receives a 4-digit PIN when creating a room. The PIN is stored in the `rooms` table. Host-only API calls include the PIN; the server validates it. Any device with the PIN can claim host controls — useful if the host switches devices. No JWT signing infrastructure needed.

**Anonymous guests.**
No accounts, no login. Each guest gets a UUID on first visit, stored in localStorage. This UUID is their identity for vote deduplication and reconnection.

**YouTube IFrame for audio.**
Each song in the catalog has a `youtubeId` in `songs.json`. The karaoke screen embeds a YouTube player using the IFrame API. The host's "Let's Sing" button calls `player.playVideo()` and records `songStartedAt` simultaneously. YouTube handles all audio licensing via their platform terms.

---

## 3. Data Design

### 3.1 Supabase Tables

**`rooms`**
```sql
CREATE TABLE rooms (
  code            CHAR(6)     PRIMARY KEY,
  state           TEXT        NOT NULL DEFAULT 'room',
  -- state values: 'room' | 'voting' | 'generating' | 'karaoke'
  host_guest_id   UUID        NOT NULL,
  host_pin        CHAR(4)     NOT NULL,
  song_id         TEXT,
  dataset_id      TEXT,
  song_started_at BIGINT,     -- Unix ms; set when host starts karaoke
  voting_ends_at  BIGINT,     -- Unix ms; set when voting round starts
  guest_count     INT         NOT NULL DEFAULT 0
);
```

**`votes_songs`**
```sql
CREATE TABLE votes_songs (
  room_code  TEXT  NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
  guest_id   UUID  NOT NULL,
  song_id    TEXT  NOT NULL,
  PRIMARY KEY (room_code, guest_id)  -- enforces one song vote per guest per room
);
```

**`votes_datasets`**
```sql
CREATE TABLE votes_datasets (
  room_code   TEXT  NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
  guest_id    UUID  NOT NULL,
  dataset_id  TEXT  NOT NULL,
  PRIMARY KEY (room_code, guest_id)  -- enforces one dataset vote per guest per room
);
```

**`lyrics`**
```sql
CREATE TABLE lyrics (
  song_id     TEXT        NOT NULL,
  dataset_id  TEXT        NOT NULL,
  lines       JSONB       NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (song_id, dataset_id)
);
```

### 3.2 Real-Time Subscriptions

Supabase Realtime is enabled on:
- `rooms` — all clients subscribe to their room row; column changes drive screen transitions
- `votes_songs` — clients subscribe to their room's vote rows for live tally updates
- `votes_datasets` — same pattern

### 3.3 Row-Level Security

| Table | Read | Write |
|---|---|---|
| `rooms` | All clients (their room row) | Server-side API routes only |
| `votes_songs` | All clients (their room's rows) | Guest may write/delete only rows where `guest_id` matches their own |
| `votes_datasets` | Same | Same |
| `lyrics` | All clients | `/api/generate` route only |

### 3.4 Static Catalog Data

Catalog data is static JSON — no database table needed for v1.

```
data/songs.json         — [{ id, title, artist, youtubeId, durationSeconds, lineCount }]
data/datasets.json      — [{ id, label, description }]
data/lrc/<id>.json      — { lines: [{ startMs, text, syllables: [{ word, count }] }] }
```

`youtubeId` is the 11-character YouTube video ID (e.g. `"dQw4w9WgXcQ"`). The karaoke screen uses this to load the YouTube IFrame player.

---

## 4. Component Design

### 4.1 Room State Machine

```
room → voting → generating → karaoke → room → ...
```

| State | Who transitions | How |
|---|---|---|
| `room` → `voting` | Host ("Start Voting") | `POST /api/rooms/:code/start-voting` |
| `voting` → `generating` | Auto (timer expires) or Host ("End Early") | Server sets state + triggers `/api/generate` |
| `generating` → `karaoke` | Auto (generation complete) | `/api/generate` updates `rooms.state` |
| `karaoke` → `room` | Host ("Next Song") | `POST /api/rooms/:code/end-song` |

All state changes update `rooms.state` in Supabase. Realtime fires to all subscribers, who switch screens on receipt.

### 4.2 Voting Logic

- Primary key on `votes_songs` and `votes_datasets` enforces one vote per guest per room
- Upsert on vote; delete on toggle-off
- Winner query (run when timer expires or host ends early):
  ```sql
  SELECT song_id FROM votes_songs
  WHERE room_code = $1
  GROUP BY song_id ORDER BY COUNT(*) DESC LIMIT 1;

  SELECT dataset_id FROM votes_datasets
  WHERE room_code = $1
  GROUP BY dataset_id ORDER BY COUNT(*) DESC LIMIT 1;
  ```
- Song and dataset winners are selected independently

### 4.3 Lyric Generation Pipeline

```
1. Receive { songId, datasetId, bustCache } from host request
2. Check lyrics table for (songId, datasetId) — return cached if bustCache=false
3. Load syllable-annotated lyrics from data/lrc/<songId>.json
4. Load dataset corpus from data/datasets/<datasetId>.txt
5. Build prompt (see API.md for prompt skeleton)
6. Call Claude API, expect JSON array response
7. Validate each line: syllable count must match original (accept ±1, log; reject >±1)
8. On rejection: retry (max 2 retries total)
9. After 3 failures: return error — host sees error, can retry manually
10. Upsert result to lyrics table
11. Update rooms.state = 'karaoke' → Supabase Realtime fires to all clients
```

### 4.4 Karaoke Timing

Sync is achieved differently for the host (TV) and guests (phones), because only the host screen has the YouTube player.

**Host screen (source of truth):**
```
Host presses "Let's Sing"
  → player.playVideo() called
  → YouTube fires onStateChange(YT.PlayerState.PLAYING)
  → At that exact moment: POST /api/rooms/:code/start-song
      body: { songStartedAt: Date.now() }
  → Server stores song_started_at; Supabase Realtime fires to all clients
  → Host RAF loop:
      positionMs = player.getCurrentTime() * 1000  ← YouTube's own clock
      currentLine = lrc.findLineAt(positionMs)
```

Using `player.getCurrentTime()` directly means the host display is frame-accurate regardless of buffering, seek, or ads. It does not drift.

**Guest phones (followers):**
```
Receive songStartedAt from Supabase Realtime
  → Start RAF loop:
      positionMs = Date.now() - songStartedAt
      currentLine = lrc.findLineAt(positionMs)
```

Guest sync is approximate (typically < 500ms off on good WiFi). This is acceptable — guests are reading along on their phones, not controlling playback.

**Why two approaches:** Only the host has the YouTube player. Guests cannot call `getCurrentTime()`. Broadcasting the player position every frame via Supabase would be too expensive. The timestamp approach is the lightest viable solution for guest phones.

### 4.5 Host PIN Flow

```
1. POST /api/rooms  →  server generates 4-digit PIN
2. Server stores PIN in rooms.host_pin
3. Response: { roomCode, hostPin }
4. Client stores hostPin in localStorage as hostPin_<roomCode>
5. Host-only API calls include { hostPin } in request body
6. Server validates: SELECT 1 FROM rooms WHERE code=$1 AND host_pin=$2
7. Any device can claim host by entering the correct PIN
```

### 4.6 YouTube Integration

- Each song in `songs.json` has a `youtubeId` field
- On the karaoke screen, the host view renders a YouTube IFrame player (can be minimized but not hidden — YouTube ToS requires the player to be visible)
- `player.playVideo()` is called when host presses "Let's Sing"; `player.stopVideo()` on song end
- Guest phone views do not render the YouTube player — they only see the lyric display

---

## 5. Screen Summary

Full screen specifications are in `docs/UX.md`. Summary:

| Screen | State | Who sees what |
|---|---|---|
| 1. Landing | — | Create Room / Join Room |
| 2. Room (between rounds) | `room` | Vote feed, search, carousels; host sees "Start Voting" |
| 3. Voting Round | `voting` | TV: live leaderboard + timer; Phone: carousels + draining bar |
| 4. Generating | `generating` | Progress bar + flavor text on all screens |
| 5. Karaoke | `karaoke` | TV: YouTube player + lyrics; Phone: lyrics only |
| 6. Recap | post-`karaoke` | Song × dataset summary; host triggers next round |

---

## 6. Deployment

### 6.1 Vercel

- Auto-deploys on push to `main`
- PR branches get preview URLs for testing
- All API routes run as Vercel serverless functions

### 6.2 Environment Variables

Set in Vercel dashboard and in local `.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=        # Supabase project URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=   # Supabase anon/publishable key
ANTHROPIC_API_KEY=               # Claude API key — server only, never NEXT_PUBLIC_
```

### 6.3 Supabase Setup Steps

1. Create a project at supabase.com (free tier)
2. Run SQL migrations from `supabase/migrations/`
3. Enable Realtime on `rooms`, `votes_songs`, `votes_datasets` in the Supabase dashboard
4. Copy the project URL and anon key to environment variables

### 6.4 Key npm Packages

| Package | Purpose |
|---|---|
| `@supabase/supabase-js` | Supabase client |
| `@supabase/ssr` | Server-side Supabase helpers for Next.js |
| `lrc-kit` | Parse LRC timing data |
| `tailwindcss` | Styling |
| `@anthropic-ai/sdk` | Claude API SDK |
