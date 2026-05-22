# AI Karaoke — UX Design Brief

## Design System

### Colors (Kahoot-inspired)

| Token | Value | Usage |
|---|---|---|
| `bg-base` | `#19191C` | Page background |
| `bg-card` | `#2B2B35` | Cards, panels |
| `accent-purple` | `#864CBF` | Primary CTA buttons, active states |
| `accent-blue` | `#1368CE` | Songs |
| `accent-orange` | `#E85C0D` | Datasets |
| `accent-yellow` | `#FFD600` | Active karaoke line highlight; voting timer bar |
| `text-primary` | `#FFFFFF` | Generated lyrics, headings |
| `text-secondary` | `#A8A8B3` | Original lyrics, labels |
| `text-muted` | `#55555F` | Dim / previous lines |
| `success` | `#26890C` | Vote confirmed, connected status |

### Typography

Use a bold, rounded sans-serif: **Nunito**, **Poppins**, or **Rubik**.

| Element | Desktop | Mobile | Weight | Color |
|---|---|---|---|---|
| Room code | 96px | 64px | 900 | white |
| Generated lyric (current) | 52px | 26px | 800 | white |
| Original lyric (current) | 22px | 13px | 400 | `text-secondary` |
| Generated lyric (next/prev) | 36px | 20px | 700 | `text-muted` |
| Original lyric (next/prev) | 16px | 11px | 400 | `text-muted` |
| UI labels / buttons | 18px | 16px | 700 | white |
| Timer / countdown | 32px | 24px | 900 | white |

### Motion

| Element | Behavior |
|---|---|
| Line transitions | Smooth upward scroll, 300ms ease-out — never instant cuts |
| Word highlight | Instant swap, 0ms — must feel beat-accurate |
| Progress bar fill | `transition: width 100ms linear` |
| Screen transitions | Cross-fade 200ms |
| Carousel drag | Native momentum scroll (`scroll-snap-type: x mandatory`) |

### Layout Rules

- `height: 100svh` (not `100vh`) on all full-screen pages — handles mobile browser chrome correctly
- `overflow-x: hidden` on root — no horizontal scroll at any breakpoint
- Minimum tap target: 48×48px on all interactive elements

---

## Responsive Breakpoints

| Breakpoint | Label | Primary View |
|---|---|---|
| < 480px | Mobile portrait | Guest / phone view |
| 480–768px | Mobile landscape | Guest view, wider grid |
| 768–1024px | Laptop | Host view, condensed |
| 1024px+ | Desktop / TV | Host view, full layout |

---

## Screens

---

### Screen 1 — Landing

**Purpose:** Entry point. Host creates a room; guest joins with a code.

**Desktop & Mobile (identical layout, vertically stacked):**
- Full-screen dark background, centered single column
- Logo / wordmark top-center
- Tagline: *"The funniest thing you can do with a browser."*
- Primary CTA (full-width, accent-purple): **Create Room**
- Divider: "or join a room"
- Text input for room code (6-char, auto-uppercase) + **Join** button (accent-blue)
- `inputmode="text"` with `autocapitalize="characters"` on the code input

---

### Screen 2 — Room (Between Rounds)

**Purpose:** Idle state between rounds. Vote feed visible, no timer. Host has a "Start Voting" button.

**Guest count:** Single unobtrusive headcount badge: "👥 8 in the room" — small, top-right. No names, no avatars.

#### Desktop (TV):
- Two columns side-by-side: **Songs** (left, blue) | **Datasets** (right, orange)
- Each column: scrollable feed sorted by vote count descending
- Each tile: title + artist (songs) or label (datasets) + vote count badge
- Tiles with more votes appear higher; feed reorders live as votes come in
- Host-only controls: **"Start Voting"** button (bottom-center, prominent)
- Manual override: host can tap any song tile and any dataset tile to pick them, then tap **"Start with This Combo"**
- Guest count badge top-right; QR code bottom-right
- No timer shown — this is the between-rounds idle state

#### Mobile (Guest):
- Fixed search bar at top (searches songs AND datasets simultaneously)
- Two stacked sections: **Songs** then **Datasets**
- Each section: horizontally scrollable carousel (snap-to-card) sorted by votes desc
- Each card: title + vote count badge + upvote button (arrow-up icon)
- Upvote states: outline arrow (not voted) → filled arrow, accent color (voted by me) → tap again to remove
- Proposing: search result not in the feed → tap adds it with count 1, appears last, rises as others vote
- One song vote and one dataset vote at a time; changeable any time
- Guest count badge: small, below search bar
- No timer shown

---

### Screen 3 — Voting Round (Timed)

**Purpose:** Active 30-second voting round. Timer visible on TV and phones.

#### Desktop (TV — Scoreboard):
- Full-screen dark background
- Large countdown timer center-top (e.g. `0:24`) — bold; turns `accent-yellow` when < 10s
- Two live leaderboards side by side:
  - **Songs** (left, blue) — ranked list with animated vote bars
  - **Datasets** (right, orange) — ranked list with animated vote bars
- Each entry: rank + title + vote bar filling proportionally
- Items reorder live as votes arrive (animated, not instant jump)
- Guest count badge top-right; QR code bottom-right
- Host-only: **"End Voting Now"** button (ends timer, picks current leaders)

#### Mobile (Guest — Vote View):
- Same search bar + two stacked carousels as Screen 2 (layout unchanged)
- **Timer:** draining full-width progress bar at the very top — `accent-yellow`, 4px height, drains from full to empty over 30 seconds; no number on mobile
- Same upvote mechanics — guests can still change votes during the round
- When timer expires: carousels dim, "Voting closed" overlay, auto-transition to Screen 4

---

### Screen 4 — Generating

**Purpose:** 7–10 second wait during Claude API call.

#### Desktop:
- Full-screen dark
- Center: Song × Dataset label — *"Bohemian Rhapsody × IKEA Manuals"* — large, bold, white
- Progress bar: 60% of screen width, rounded, fills from 0 → ~90% (never completes until lyrics arrive)
- Rotating flavor text beneath, changes every 2.5s with fade-in:
  - *"Measuring in millimeters…"*
  - *"Consulting the manual…"*
  - *"The AI is taking notes…"*
  - *"Counting syllables…"*
- QR code bottom-right

#### Mobile:
- Same structure, full-width progress bar, flavor text below

---

### Screen 5 — Karaoke Display

**This is the hero screen. Design it like a broadcast.**

---

#### Syllable Grid — The Core Rule

Each lyric unit is a **generated line paired with its original below it**, aligned **syllable by syllable** in a shared CSS grid. The generated line is always on top (large, white). The original is always below it (small, gray).

**Grid spec:**
```css
grid-template-columns: repeat(N, 1fr)  /* N = total syllable count of the line */
```

Each word's `grid-column` is computed from its cumulative start syllable + `span syllableCount`.

```
col:   1       2       3       4       5
gen:  [is    ][this  ][the   ][real  ][life  ]   ← 1 col each
orig: [fix   ][the   ][shelf ][right ][now   ]   ← 1 col each

col:   1──────2       3       4       5
gen:  [tight·en      ][the   ][left  ][bolt  ]   ← tight·en spans 2 cols
orig: [is    ][this  ][the   ][real  ][life  ]   ← 1 col each
```

**Wrap rule — CRITICAL:** If the syllable grid is too wide for the screen, split at the same syllable-column boundary for both rows. Never let the two rows wrap independently.

✅ CORRECT:
```
[is    ][this  ][the   ]   ← generated cols 1–3
[fix   ][the   ][shelf ]   ← original  cols 1–3

[right ][now   ]           ← generated cols 4–5
[real  ][life  ]           ← original  cols 4–5
```

❌ WRONG — rows wrap at different points, syllable alignment is lost.

---

#### Line Highlight (v1)

The entire current active line has an `accent-yellow` background bar behind both rows. Word-level highlighting is post-MVP.

| Line state | Generated | Original |
|---|---|---|
| Previous | `text-muted`, 20% opacity | `text-muted`, 20% opacity |
| **Current** | **White, full opacity + yellow bar** | **`text-secondary`, full opacity** |
| Next | `text-muted`, 40% opacity | `text-muted`, 40% opacity |

---

#### Song Progress Bar

- Full-width, fixed at bottom: 8px on desktop, 4px on mobile
- `accent-yellow` fill on `bg-card` track
- Fills left-to-right as song progresses
- Driven by `player.getCurrentTime()` (host) or `Date.now() - songStartedAt` (guests), updated every 100ms
- Display-only in v1 (no scrubbing)
- Time label right-aligned: `2:14 / 5:54`

---

#### Desktop (TV) Full Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  🎵 Bohemian Rhapsody × 📋 IKEA Manuals   [Regenerate]   [QR]  │  ← fixed top bar
├──────────────────────────────────────────────────────────────────┤
│  [YouTube player — minimized, top-right corner of content area]  │
│                                                                  │
│  ── previous line (20% opacity) ─────────────────────────────── │
│  [prev generated…]                                               │
│  [prev original…]                                                │
│                                                                  │
│  ══ CURRENT LINE ═══════════════════════════════════════════════ │
│  Fix     the     shelf    right    now                           │  52px bold white
│  Is      this    the      real     life                          │  22px gray
│  (accent-yellow background bar behind both rows)                 │
│                                                                  │
│  ── next line (40% opacity) ─────────────────────────────────── │
│  [next generated…]                                               │
│  [next original…]                                                │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░   2:14 / 5:54         │  ← progress bar
└──────────────────────────────────────────────────────────────────┘
```

**Top bar (fixed):** Song × dataset label with emoji | Regenerate button (host only, ghost style, small) | QR code (120×120px)

**YouTube player:** Visible as required by YouTube ToS. Position: small, minimized in top-right of the content area. Does not obstruct lyrics.

**Line display area:** 3 lyric units visible. Current line full opacity + highlight. Lines slide upward as song progresses.

---

#### Mobile (Guest Companion)

```
┌────────────────────────────┐
│  🎵 Boh. Rhapsody × IKEA  │  ← small top badge
├────────────────────────────┤
│  [prev generated - small]  │  20px, dim
│  [prev original - small]   │  11px, dim
│                            │
│ ╔══════════════════════╗   │
│ ║  Fix  the  shelf    ║   │  26px bold white + yellow bar
│ ║  Is   this  the     ║   │  13px gray
│ ║                      ║   │
│ ║  right    now        ║   │  (wrapped — both rows break together)
│ ║  real     life       ║   │
│ ╚══════════════════════╝   │
│                            │
│  [next generated - small]  │  20px, dim
│  [next original - small]   │  11px, dim
│                            │
├────────────────────────────┤
│  ████████░░░░░░░░░░  2:14  │  ← progress bar, 4px
└────────────────────────────┘
```

- No YouTube player on guest phones
- `height: 100svh` — accounts for mobile browser chrome
- No horizontal scroll — columns shrink proportionally; wrap rule applies if still too wide
- Connection status dot: small, top-right corner

---

### Screen 6 — Recap

**Purpose:** Brief pause between songs.

#### Desktop:
- Song × dataset combo just played (large)
- Optional stretch goal: spotlight one lyric line — *"Best line: 'Fix the shelf right now'"*
- CTA: **"Next Round"** (host only, returns to Screen 2)
- Guest count still visible; QR persists

#### Mobile:
- Same info, condensed
- Auto-transitions to Screen 2 when host triggers next round

---

## QR Code — Persistence Rule

The QR code **must appear in the bottom-right corner of every screen after room creation**. Minimum size: 120×120px. It encodes the join URL and is never hidden — a late arrival must be able to scan it mid-song.

---

## Host-Only Controls

Visible only when `localStorage` contains `hostPin_<roomCode>`:

| Control | Screen | Placement |
|---|---|---|
| Start Voting | Room Screen (2) | Bottom center, large |
| Start with This Combo | Room Screen (2) | Bottom center, after manual tile selection |
| End Voting Now | Voting Round (3) | Bottom center |
| Let's Sing | Post-generation (4) | Full-width primary button |
| Regenerate | Karaoke (5) | Top bar, small ghost button |
| Next Round | Recap (6) | Center, primary button |

---

## Accessibility

- All tap targets: minimum 48×48px
- Minimum contrast: 4.5:1 on all text (dim-room condition)
- No color-only affordances — pair color with shape or icon
- Font never below 13px
- Progress bars: `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`

---

## Open Questions for the Designer

1. **Always show original lyrics, or offer a toggle?** Current spec always shows them (small, gray). A toggle would free vertical space on mobile but removes the singability reference.
2. **Search results on mobile:** Single unified list for songs + datasets, or keep them in separate sections?
3. **Host on mobile?** If the host uses a phone as the primary display, Regenerate and Let's Sing need to be prominent on mobile too.
