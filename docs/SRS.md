# AI Karaoke — Software Requirements Specification

## 1. Introduction

### 1.1 Purpose
This document defines what AI Karaoke will do — every feature, constraint, and acceptance condition. It is the source of truth for scope decisions.

### 1.2 Scope
Web app for same-room groups. One host (laptop/TV), multiple guests (phones). Audio plays via YouTube IFrame on the host screen. Guests join anonymously.

### 1.3 Definitions

| Term | Definition |
|---|---|
| Room | A single session identified by a unique 6-character code |
| Host | The person who created the room, authenticated by PIN |
| Guest | Any anonymous participant who joined via QR code or room code |
| Song | A track with LRC timing data and syllable-annotated lyrics |
| Dataset | A text corpus used as source material for AI lyric rewriting |
| Combo | A paired song + dataset selected by vote |
| Line | One lyric unit — a generated row stacked above its original row |
| Syllable grid | CSS layout where each column represents one syllable position |

---

## 2. Functional Requirements

### FR-1 — Create Room
The system shall create a room with a unique 6-character alphanumeric code when a host requests it. Room creation must complete in under 2 seconds.

### FR-2 — Host Identity
The device that creates the room is the host. Its guest UUID is stored as `host_guest_id` in the room. Host controls are shown on any client whose localStorage UUID matches `host_guest_id`.

### FR-3 — Join Room
Guests shall join a room by entering the room code manually or scanning a QR code. Access is instant — any browser, no install, no account.

### FR-4 — QR Code Persistence
A QR code encoding the join URL shall be visible in the bottom-right corner of every screen after room creation. It is always visible.

### FR-5 — Guest Count
A live headcount badge shall display the number of guests currently in the room, updated in real time.

### FR-6 — Room State Machine
Rooms shall transition through states in this order:
```
room → voting → generating → karaoke → room → ...
```
Every state transition is broadcast to all connected clients, who switch screens on receipt.

### FR-7 — Anonymous Guest Identity
Guests are identified by a UUID generated client-side on first visit and stored in localStorage. Only data stored: the UUID and vote selections.

### FR-8 — Reconnection
On reconnect, the client shall read the current room state via REST and jump to the correct screen. No re-join prompt, no data loss.

### FR-9 — Vote Feed
In `room` state, guests shall see a browseable feed of songs and datasets sorted by vote count descending, updated in real time.

### FR-10 — Search and Propose
Guests shall be able to search the catalog. If a result is not yet in the feed, selecting it adds it with 1 vote (the guest's). It appears at the bottom of the feed and rises as others vote for it.

### FR-11 — Upvote Toggle
Tapping a song card votes for it; tapping again removes the vote. Each guest holds at most 1 song vote and 1 dataset vote at a time. Changing a vote removes the previous one.

### FR-12 — Start Voting Round
The host shall be able to start a 30-second timed voting round, transitioning the room from `room` → `voting` state.

### FR-13 — Voting Screen Display
During `voting` state:
- **TV (host screen):** Large numeric countdown center-top + two live leaderboards side by side — Songs (left) and Datasets (right). Each entry shows rank, title, and a vote bar that fills proportionally and reorders in real time as votes come in.
- **Phones (guests):** Same vote feed and carousels as the between-rounds screen, with a draining full-width progress bar at the top showing time remaining.

### FR-14 — Auto-Select Winner
When the timer expires, the system shall automatically select the top-voted song and top-voted dataset independently, then transition to `generating` state and trigger AI generation.

### FR-15 — Host Early End
The host may end the voting round before the timer expires, triggering the same auto-select logic immediately.

### FR-16 — Real-Time Vote Tally
Vote tallies shall update on all connected clients within 500ms of a vote being cast, without any page refresh.

### FR-17 — Generate Lyrics
The system shall call the Claude API to rewrite song lyrics using the selected dataset as source material.

### FR-18 — Syllable Constraint (Hard)
Every generated line must have exactly the same syllable count as the original line it replaces. This is a hard constraint.

### FR-19 — Dataset Constraint
Generated words must be drawn from the dataset corpus. The model may combine or lightly modify words but not invent freely.

### FR-20 — Rhyme Preservation (Soft)
The system should preserve end-rhymes where possible, but never at the cost of the syllable constraint.

### FR-21 — Structured JSON Output
The Claude API must return a JSON array of line objects. Free-form text responses are rejected and trigger a retry.

### FR-22 — Syllable Validation and Retry
The system shall validate syllable counts on every returned line using the CMU Pronouncing Dictionary (fallback: heuristic splitter).
- Mismatch of exactly 1 syllable: accept and log
- Mismatch > 1 syllable: retry the full generation (max 2 retries)
- After 3 total failures: surface an error message to the host

### FR-23 — Lyric Cache
Generated lyrics for a given song × dataset combo are cached in the database. Subsequent requests for the same combo return the cached result unless the host forces a refresh.

### FR-24 — Regenerate
The host may request a fresh generation for the current combo, bypassing the cache. Old lyrics remain visible on all clients until new lyrics arrive.

### FR-25 — Generation Progress Feedback
During generation, a progress bar and rotating flavor text shall appear on all clients. Progress feedback must appear within 1 second of generation being triggered.

### FR-26 — Syllable Grid Layout
Lyrics shall be rendered in a CSS grid where each column represents one syllable. The generated line (row 1) sits directly above the original line (row 2), syllable-aligned.

### FR-27 — Multi-Syllable Word Spanning
Words with multiple syllables span multiple grid columns using `grid-column: span N`.

### FR-28 — Synchronized Line Wrapping
If a line is too wide for the screen, both rows (generated + original) must wrap at the same syllable-column boundary. Both rows always wrap together at the same syllable-column boundary.

### FR-29 — Line Highlight
The current active line shall be highlighted with an accent-yellow full-line background bar. Previous and next lines are visible at reduced opacity.

### FR-30 — In-App Audio Playback
The karaoke screen shall embed a YouTube IFrame player. Each song in the catalog has a `youtubeId`. The player is visible on the host/TV screen. Guest phones show the lyric display.

### FR-31 — Karaoke Timing Sync
When the host presses "Let's Sing", the YouTube player starts and `songStartedAt` is recorded in the database when YouTube fires `onStateChange(PLAYING)`.

- **Host screen:** uses `player.getCurrentTime() * 1000` in a requestAnimationFrame loop for frame-accurate line highlighting synchronized to actual audio playback.
- **Guest phones:** use `Date.now() - songStartedAt` in a requestAnimationFrame loop. Expected drift < 500ms on good WiFi, acceptable for reading lyrics.

### FR-32 — Song Progress Bar
A full-width progress bar fixed at the bottom of the karaoke screen shows song progress, driven by `player.getCurrentTime()` on the host and by `Date.now() - songStartedAt` on guest phones.

### FR-33 — Song × Dataset Label
The top bar of the karaoke screen shows the current song × dataset combo label at all times during playback.

### FR-34 — Mobile Lyrics View
Guest phones shall display the same lyric display as the TV (no audio player), synced via the `songStartedAt` timestamp.

### FR-35 — Auto-Switch After Song
When the song ends, all screens shall automatically transition to the recap screen.

### FR-36 — Connection Status Indicator
A small colored dot shall indicate real-time connection status on guest phones: green = connected, amber pulsing = reconnecting.

### FR-37 — Recap Screen
After the song ends, a brief recap screen shows the song × dataset combo just played. The host triggers the return to the vote feed.

---

## 3. Non-Functional Requirements

### 3.1 Performance

| Requirement | Target |
|---|---|
| Room creation | < 2 seconds |
| QR scan → vote feed visible | < 3 seconds |
| Vote update visible on all clients | < 500ms |
| Generation progress feedback | < 1 second after host triggers |
| Total AI generation time | < 10 seconds |
| Host karaoke sync (audio ↔ lyrics) | Frame-accurate (uses YouTube `getCurrentTime()`) |
| Guest karaoke sync drift vs. host | < 500ms on good WiFi |

### 3.2 Reliability

- Good WiFi environment is assumed.
- Votes are persisted to the server immediately on submit.
- On reconnect, clients restore state from a REST endpoint — guests resume exactly where they left off.

### 3.3 Security

- Host controls are gated by a 4-digit room PIN (stored server-side, entered once and cached in localStorage).
- The Claude API key stays server-side; all AI calls go through a server-side API route.
- Only anonymous data is stored: UUIDs and vote selections.

### 3.4 Scale (v1 targets)

- Up to 20 guests per room.
- Single-room use case (one party at a time).

---

## 4. User Stories and Acceptance Criteria

### US-1: Host creates a room
**As a host**, I want to create a room instantly so guests can join with minimal friction.

- Clicking "Create Room" creates a room in < 2 seconds
- A 6-character room code and QR code are shown immediately
- The host is taken directly to the room screen with host controls visible

### US-2: Guest joins by scanning QR
**As a guest**, I want to scan a QR code and be in the session immediately.

- Scanning opens the app in any browser — instant access, works immediately
- Guest lands directly on the vote feed
- Guest count badge increments on all screens within 500ms

### US-3: Late arrival joins mid-song
**As a late guest**, I want to join during an active song and see the right screen.

- Joining mid-song shows the karaoke view synced to the current line (< 100ms drift)
- Joining between songs shows the vote feed
- QR code is visible on every screen

### US-4: Guest votes for a song and dataset
**As a guest**, I want to vote from my phone.

- Guest can search songs and datasets by name
- Tapping a card votes for it; tapping again removes the vote
- Only one song vote and one dataset vote per guest at a time
- Changes are reflected on the TV within 500ms

### US-5: Host starts a voting round
**As a host**, I want to start a timed round.

- "Start Voting" is visible only to the host
- Pressing it starts a 30-second countdown
- TV shows a live leaderboard with vote bars; phones show a draining progress bar
- When the timer hits zero, the top song and dataset are auto-selected

### US-6: AI generates lyrics
**As a group**, we want lyrics generated and shown to everyone.

- Generation starts automatically after voting ends
- All clients see "The AI is cooking…" within 1 second
- Progress bar animates; flavor text rotates every 2.5 seconds
- Lyrics appear on all clients when generation is complete

### US-7: Group sings the generated lyrics
**As a group**, we want to read lyrics that are clearly readable and syllable-aligned.

- Generated words (large, white) sit above original words (small, gray) in the same syllable column
- Current line has a yellow background bar; previous and next lines are visible at reduced opacity
- Line transitions are a smooth upward scroll (300ms)
- Font is readable from 3 meters (min 52px for current generated line on desktop)

### US-8: Host regenerates bad lyrics
**As a host**, I want to request new lyrics if the AI output is unsatisfying.

- "Regenerate" button is visible to the host at all times during karaoke
- Tapping it shows the generation screen again; old lyrics stay visible until new ones arrive
- New generation always bypasses the cache

### US-9: Phone sleeps and reconnects
**As a guest**, I want my vote preserved and my screen restored after a reconnect.

- Votes are saved to the server immediately on submit
- On reconnect, the client reads current room state and jumps to the correct screen
- Guest UUID from localStorage persists — guests resume exactly where they left off

---

## 5. Catalog (v1 Seed Data)

### Songs

| Song | Artist |
|---|---|
| Bohemian Rhapsody | Queen |
| Never Gonna Give You Up | Rick Astley |
| Africa | Toto |
| Someone Like You | Adele |
| Don't Stop Believin' | Journey |

LRC timing files are pre-built as static JSON in `data/lrc/`. Timestamps are approximations; fetch from lrclib.net to improve accuracy.

### Datasets

| Dataset | Description |
|---|---|
| Yelp Reviews (1-star) | Furious customer complaints |
| IKEA Manuals | Step-by-step assembly instructions |
| Legal Disclaimers | Terms of service boilerplate |
| Horoscopes | Vague cosmic predictions |
| Craigslist Ads | Chaotic classified listings |
