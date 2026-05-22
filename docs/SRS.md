# AI Karaoke — Software Requirements Specification

## 1. Introduction

### 1.1 Purpose
Defines what AI Karaoke will do in each version. Source of truth for scope decisions.

### 1.2 Definitions

| Term | Definition |
|---|---|
| Host | The person running the app on the laptop/TV |
| Song | A track with LRC timing data and syllable-annotated lyrics |
| Dataset | A text corpus used as source material for AI lyric rewriting |
| Combo | A paired song + dataset |
| Line | One lyric unit — generated row stacked above original row |
| Syllable grid | CSS layout where each column = one syllable position |

---

## 2. v1 — Single Device

### 2.1 Scope
A web app that runs on one device — a laptop or TV. The host uses it to pick a song and a dataset, generate AI-rewritten lyrics, and sing along to the music playing on screen.

### 2.2 Functional Requirements

#### FR-1 — Song Browser
The host shall see a searchable catalog of songs displayed as cards. Each card shows title, artist, and duration. The host can type to filter and tap a card to select it.

#### FR-2 — Dataset Browser
The host shall see a searchable catalog of datasets displayed as cards. Each card shows the label and a short description. The host can type to filter and tap a card to select it.

#### FR-3 — Generate
With a song and dataset selected, the host taps **Generate**. The system calls the Claude API and rewrites the song's lyrics syllable-for-syllable using the dataset as source material.

#### FR-4 — Lyrics Cache
Generated lyrics for a given song × dataset combo are cached in localStorage for the duration of the session. Re-selecting the same combo returns the cached result instantly. The host can force a fresh generation at any time.

#### FR-5 — Generation Progress
During generation, a progress screen shows the song × dataset combo name, an animated progress bar, and rotating flavor text. Progress feedback must appear within 1 second of the host tapping Generate.

#### FR-6 — Syllable Constraint (Hard)
Every generated line must have exactly the same syllable count as the original.

#### FR-7 — Dataset Constraint
Generated words are drawn from the dataset corpus. The model may combine or lightly modify words.

#### FR-8 — Rhyme Preservation (Soft)
End-rhymes are preserved where possible, without violating FR-6.

#### FR-9 — Structured Output + Validation
Claude returns a JSON array of line objects. The server validates syllable counts on every line using the CMU Pronouncing Dictionary (fallback: heuristic splitter).
- Off by 1 syllable: accept and log
- Off by > 1 syllable: retry (max 2 retries)
- After 3 failures: show error, let host retry manually

#### FR-10 — Play
The host taps **Play**. The YouTube IFrame player starts and `songStartedAt` is recorded simultaneously when YouTube fires `onStateChange(PLAYING)`.

#### FR-11 — Syllable Grid Display
Lyrics are rendered in a CSS grid where each column = one syllable. Generated line (row 1, large, white) sits directly above original line (row 2, small, gray), syllable-aligned.

#### FR-12 — Multi-Syllable Word Spanning
Words with multiple syllables span multiple grid columns (`grid-column: span N`).

#### FR-13 — Synchronized Line Wrapping
Both rows always wrap together at the same syllable-column boundary.

#### FR-14 — Line Highlight
The current active line has an accent-yellow full-line background bar. Previous and next lines are visible at reduced opacity.

#### FR-15 — Frame-Accurate Timing
The host screen uses `player.getCurrentTime() * 1000` in a requestAnimationFrame loop to highlight the correct line in sync with audio playback.

#### FR-16 — Song Progress Bar
A full-width progress bar at the bottom shows song progress, driven by `player.getCurrentTime()`, updated every 100ms.

#### FR-17 — Song × Dataset Label
The top bar shows the current song × dataset combo at all times during playback.

#### FR-18 — Regenerate
The host can request a fresh generation at any time, bypassing the cache. Old lyrics stay visible until new ones arrive.

#### FR-19 — Back to Picker
After a song or at any point, the host can return to the song/dataset picker to start a new combo.

### 2.3 Non-Functional Requirements

#### Performance
| Requirement | Target |
|---|---|
| Time to first screen | < 2 seconds |
| Generation progress feedback | < 1 second after Generate is tapped |
| Total generation time | < 10 seconds |
| Karaoke sync (lyrics ↔ audio) | Frame-accurate via `getCurrentTime()` |

#### Reliability
- Good WiFi assumed (Claude API call requires network)
- localStorage cache survives page refreshes within the same session

#### Security
- `ANTHROPIC_API_KEY` stays server-side in a single Vercel serverless function
- No user data collected or stored beyond the current session

### 2.4 User Stories

#### US-1: Host picks a combo and generates
**As a host**, I want to quickly find a song and a dataset and generate rewritten lyrics.

- I see searchable card grids for songs and datasets on one screen
- I type to filter; matching cards appear immediately
- I tap a song card and a dataset card to select them — both show as selected
- I tap Generate; the progress screen appears within 1 second
- Lyrics appear within 10 seconds

#### US-2: Host sings along
**As a host**, I want to see the lyrics on screen in sync with the music.

- Tapping Play starts the YouTube player and the lyric display simultaneously
- The current line is highlighted in yellow; previous and next lines are visible
- Generated words (large, white) sit directly above original words (small, gray) in the same syllable column
- Font is readable from 3 meters on a laptop screen

#### US-3: Host regenerates bad lyrics
**As a host**, I want to get different lyrics if the AI output isn't funny.

- A Regenerate button is always visible during playback
- Tapping it shows the progress screen; old lyrics stay visible until new ones arrive
- The new result is different from the cached one

#### US-4: Host picks a new combo
**As a host**, I want to try a different song or dataset without refreshing the page.

- A "New Combo" button is always visible
- Tapping it returns to the picker with previous selections cleared
- Previously generated combos remain in the localStorage cache for the session

### 2.5 v1 Catalog

#### Songs
| Song | Artist |
|---|---|
| Bohemian Rhapsody | Queen |
| Never Gonna Give You Up | Rick Astley |
| Africa | Toto |
| Someone Like You | Adele |
| Don't Stop Believin' | Journey |

LRC timing files are pre-built as static JSON in `data/lrc/`. Fetch from lrclib.net to improve accuracy.

#### Datasets
| Dataset | Description |
|---|---|
| Yelp Reviews (1-star) | Furious customer complaints |
| IKEA Manuals | Step-by-step assembly instructions |
| Legal Disclaimers | Terms of service boilerplate |
| Horoscopes | Vague cosmic predictions |
| Craigslist Ads | Chaotic classified listings |

---

## 3. v2 — Phones Join

Guests join from their phones via QR code or room code. No account required. Optional nickname for display purposes only.

### 3.1 New in v2
- Room creation with a 6-character code + QR code
- Guests join from their phones — optional nickname at join
- Live vote feed on phones: songs and datasets displayed as carousels, sorted by vote count
- 30-second timed voting round started by the host
- TV shows live leaderboard during voting; phones show draining progress bar
- Top-voted song × top-voted dataset (independently) auto-selected when timer ends
- Guest phones show companion lyric view synced to the TV via `songStartedAt` timestamp
- Guest count badge on all host screens
- Reconnection: clients restore state on reconnect, resume where they left off

### 3.2 v2 Architecture Additions
- Supabase (real-time + DB): rooms table, votes tables, replaces localStorage
- Supabase Realtime: state transitions broadcast to all clients
- Guest UUID in localStorage as anonymous identity

---

## 4. v3 — History + Ratings

### 4.1 New in v3
- After each song, all guests rate the combo 1–5 stars
- Ratings are averaged and stored per combo per device
- Host sees a "Greatest Hits" catalog: all combos played on this device, sorted by average rating
- Host can replay any past combo (uses cached lyrics)
- Combos catalog is stored per-device in localStorage
