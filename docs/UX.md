# AI Karaoke — UX Design Brief

## Design System

### Aesthetic Direction

**Modern dark with depth.** Near-black background, glass-morphism cards, gradient accents, and subtle glow effects. The energy and interaction patterns come from Kahoot — large text, instant feedback, clear visual hierarchy — but the visual language is closer to Linear, Vercel, or Arc: precise, premium, slightly electric.

### Colors

| Token | Value | Usage |
|---|---|---|
| `bg-base` | `#09090B` | Page background (near-black) |
| `bg-card` | `rgba(255,255,255,0.05)` + `backdrop-filter: blur(12px)` | Glass cards and panels |
| `border-subtle` | `rgba(255,255,255,0.08)` | Card borders, dividers |
| `gradient-primary` | `#7C3AED → #2563EB` (135deg) | CTA buttons, active states |
| `accent-violet` | `#7C3AED` | Song cards, song-related UI |
| `accent-cyan` | `#06B6D4` | Dataset cards, dataset-related UI |
| `highlight` | `#A78BFA` with `box-shadow: 0 0 24px rgba(167,139,250,0.4)` | Active karaoke line — soft violet glow |
| `text-primary` | `#F8FAFC` | Generated lyrics, headings |
| `text-secondary` | `#94A3B8` | Original lyrics, labels |
| `text-muted` | `#3F3F46` | Dim / previous lines |
| `success` | `#10B981` | Generation complete, confirmed states |

### Typography

**Inter** or **Geist** for UI. **Cal Sans** or **Syne** for display headings if available; otherwise Inter at weight 800. Clean, geometric, legible at distance.

| Element | Desktop | Mobile | Weight | Color |
|---|---|---|---|---|
| Generated lyric (current) | 52px | 26px | 800 | `text-primary` |
| Original lyric (current) | 22px | 13px | 400 | `text-secondary` |
| Generated lyric (next/prev) | 36px | 20px | 700 | `text-muted` |
| Original lyric (next/prev) | 16px | 11px | 400 | `text-muted` |
| Card title | 18px | 16px | 600 | `text-primary` |
| UI labels / buttons | 15px | 14px | 500 | `text-primary` |

### Surface Treatment

**Glass cards:** `background: rgba(255,255,255,0.05); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;`

**Selected card:** swap border to a gradient stroke — `border: 1px solid transparent; background-clip: padding-box;` with a gradient pseudo-border using the accent color. Add a faint glow: `box-shadow: 0 0 20px rgba(124,58,237,0.3)` for songs, `rgba(6,182,212,0.3)` for datasets.

**Primary button:** gradient background `linear-gradient(135deg, #7C3AED, #2563EB)`, `border-radius: 12px`, no border, subtle inner highlight on top edge via `box-shadow: inset 0 1px 0 rgba(255,255,255,0.15)`.

**Background depth:** A very subtle radial gradient behind the content — `radial-gradient(ellipse 80% 50% at 50% -10%, rgba(124,58,237,0.15), transparent)` — gives the page a faint glow from above without being distracting.

### Motion

| Element | Behavior |
|---|---|
| Line transitions | Smooth upward scroll, 300ms ease-out |
| Active line glow | Fade in `box-shadow` over 150ms when line becomes active |
| Progress bar fill | `transition: width 100ms linear` |
| Screen transitions | Cross-fade 200ms |
| Card selection | Scale to 1.02 + gradient border + glow, 120ms ease-out |
| Button hover | Brightness 1.1 + subtle lift `translateY(-1px)`, 100ms |
| Flavor text | Fade-out 300ms → swap → fade-in 300ms |

### Layout Rules

- `height: 100svh` on all full-screen pages
- `overflow-x: hidden` on root — all content contained within 100vw
- Minimum tap target: 48×48px on all interactive elements
- Minimum font size: 13px
- Border radius: 16px for cards, 12px for buttons, 8px for small elements

---

## Screens (v1)

v1 has three screens: **Picker → Generating → Karaoke**

---

### Screen 1 — Picker

**Purpose:** Host selects a song and a dataset, then generates.

```
┌────────────────────────────────────────────────────────────────────────┐
│  AI Karaoke                                                            │
│  "The AI rewrote your songs. You still have to sing them."             │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   🎵 Songs                        📋 Datasets                         │
│   🔍 [search songs...    ]        🔍 [search datasets...    ]         │
│                                                                        │
│  ┌──────────────────────────────┐ ┌──────────────────────────────┐    │
│  │ Bohemian Rhapsody          ↑ │ │ Yelp Reviews (1-star)      ↑ │    │
│  │ Queen · 5:54                 │ │ Furious customer complaints  │    │
│  ├──────────────────────────────┤ ├──────────────────────────────┤    │
│  │ Never Gonna Give You Up      │ │ IKEA Manuals                 │    │  ← selected
│  │ Rick Astley · 3:33           │ │ Step-by-step assembly ins…   │    │
│  ├──────────────────────────────┤ ├──────────────────────────────┤    │
│  │ Africa                     ↓ │ │ Legal Disclaimers            │    │
│  │ Toto · 4:55                  │ │ Terms of service boilerplate │    │
│  └──────────────────────────────┘ ├──────────────────────────────┤    │
│                                   │ Horoscopes                 ↓ │    │
│                                   │ Vague cosmic predictions    │    │
│                                   └──────────────────────────────┘    │
│                                                                        │
│        [ Generate: Never Gonna Give You Up × IKEA Manuals ]           │
│                    ← accent-purple, full-width →                       │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Layout:**
- Two equal-width columns side by side: **Songs** on the left, **Datasets** on the right
- Songs column has a subtle violet background tint (`rgba(124,58,237,0.04)`); Datasets column has a subtle cyan tint (`rgba(6,182,212,0.04)`) — makes the two halves visually distinct at a glance
- Each column has a section header (violet for Songs, cyan for Datasets), a search bar, and a vertically scrollable list of cards below
- The scrollable card list has horizontal padding large enough that selected cards' glow and scale are never clipped
- Cards are full-width within their column — horizontal items, not square tiles

**Card anatomy (Song):**
```
┌─────────────────────────────────────────────┐
│  Bohemian Rhapsody                           │  ← title, 18px, weight 600, text-primary
│  Queen · 5:54                                │  ← artist · duration, 14px, text-secondary
└─────────────────────────────────────────────┘
```

**Card anatomy (Dataset):**
```
┌─────────────────────────────────────────────┐
│  IKEA Manuals                                │  ← label, 18px, weight 600, text-primary
│  Step-by-step assembly instructions          │  ← description, 14px, text-secondary
└─────────────────────────────────────────────┘
```

**Selected state:**
- Song card selected: `border: 1px solid rgba(124,58,237,0.6)` + `box-shadow: 0 0 20px rgba(124,58,237,0.3)` + `background: rgba(124,58,237,0.08)` + `scale(1.02)`
- Dataset card selected: same treatment using cyan — `box-shadow: 0 0 20px rgba(6,182,212,0.3)` + `background: rgba(6,182,212,0.08)`
- Card list scroll container has `padding: 4px 8px` so the scale + glow are never clipped by overflow
- Selection persists while the host searches — the selected card remains highlighted even if scrolled out of view

**Generate button:**
- Spans the full width of both columns combined, pinned to the bottom of the screen
- Always shows the current selection state as a fill-in-the-blank:
  - Neither selected: *"Select a song and a dataset to generate"* — disabled, 40% opacity
  - Song only: *"🎵 Bohemian Rhapsody × pick a dataset"* — disabled, 40% opacity
  - Dataset only: *"pick a song × 📋 IKEA Manuals"* — disabled, 40% opacity
  - Both selected: *"Generate: Bohemian Rhapsody × IKEA Manuals"* — fully active, gradient background

**Search:** Each column has its own search bar. Typing filters that column's card list in real time. Cards not matching the query disappear immediately; the selected card reappears if the query is cleared. Shows *"No matches"* if nothing in that column matches.

**Rationale for two columns:** The app runs on landscape screens (laptop, TV). A two-column layout fills horizontal space naturally, keeps both choices visible simultaneously without scrolling past each other, and mirrors the left-to-right selection flow: pick a song, then pick a dataset, then generate.

---

### Screen 2 — Generating

**Purpose:** 7–10 second wait during Claude API call.

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                                                          │
│         🎵 Bohemian Rhapsody × 📋 IKEA Manuals          │
│                    large, bold, white                    │
│                                                          │
│         ████████████████░░░░░░░░░░░░░░░░░░░░░░          │
│                    60% wide, rounded                     │
│                                                          │
│              "Counting syllables…"                       │
│              flavor text, fades every 2.5s               │
│                                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Flavor text rotation** (2.5s fade, loops):
- *"Counting syllables…"*
- *"Consulting the manual…"*
- *"The AI is taking notes…"*
- *"Measuring in millimeters…"*
- *"Cross-referencing the reviews…"*

**Progress bar:** Fills from 0 → ~90% during generation. Completes to 100% when lyrics arrive.

**On error:** Progress stops. Flavor text replaced with: *"Generation failed — tap to try again."* Tapping returns to Picker with the same selections intact.

---

### Screen 3 — Karaoke

**Purpose:** Audio plays; lyrics scroll in sync. This is the hero screen.

```
┌──────────────────────────────────────────────────────────────────┐
│  🎵 Bohemian Rhapsody × 📋 IKEA Manuals   [Regenerate] [New]    │  ← top bar (fixed)
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Check   the   di-a-gram  care-ful-ly      ← past line, muted   │
│  No      es-   cape       from  re-al-i-ty                      │
│                                                                  │
│  ══════════════════════════════════════════════════════════════  │
│  Fix     the   shelf      right  now        ← ACTIVE line        │  52px bold, glow
│  Is      this  the        real   life                            │  22px gray
│  ░░░░[word highlight — amber glow]░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  ══════════════════════════════════════════════════════════════  │
│                                                                  │
│  Tigh-   ten   all        the    four  bolts ← next line, muted  │
│  Is      this  just       fan-   ta-   sy                        │
│                                                                  │
│  O-      pen   your       eyes   ← further lines, more muted     │
│  ...                                                             │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  [▶/❚❚]  ████████████████░░░░░░░░░░░░░  2:14 / 5:54  [YouTube]  │  ← bottom bar (fixed)
└──────────────────────────────────────────────────────────────────┘
```

**Top bar (fixed):**
- Left: song × dataset label with emoji icons
- Right: **Regenerate** (ghost, small) + **New Combo** (ghost, small)

**Lyrics area (scrollable):**
- All lyric lines are rendered in a vertically scrollable list — the full song is visible by scrolling
- The active line has full opacity and a left-side violet glow bar accent
- Lines before the active: progressively dimmer as they recede (previous = 60% opacity, earlier = 30%)
- Lines after the active: slightly dimmed (70% opacity) — upcoming, not forgotten
- Active line slides into focus: 300ms ease-out (`translateY(16px) → 0, opacity 0.6 → 1`)
- Font: 52px generated / 22px original for the active line; proportionally smaller for context lines
- **Auto-scroll:** the view automatically scrolls to keep the active line centered. If the user manually scrolls, auto-scroll pauses and resumes after 3 seconds of inactivity.

**Word-level highlight:**
Within the active line, the word currently being sung is highlighted in amber (`#FCD34D`) with a soft golden glow. In v1, timing is syllable-proportional: `(syllablesInWord / totalSyllablesInLine) × lineDurationMs`, where `syllablesInWord = word.length` in the lyric line format. When `data/lrc/<id>-words.json` exists, use per-word `startMs`/`endMs` instead.

**Bottom bar (fixed):**
- **▶/❚❚ button** — toggles play/pause
- **Seekbar** — full-width scrubable range input, gradient fill (`#7C3AED → #06B6D4`). Dragging the seekbar pauses auto-scroll and jumps playback to the new position.
- **Time label** — current time / total duration, e.g. `2:14 / 5:54`
- **YouTube player** — always rendered per YouTube ToS, minimized to ~80×45px at the right edge of the bottom bar

**Playback start:**
- On first load, playback is paused at 0:00
- Tapping ▶ starts the YouTube player and the timing loop simultaneously
- No overlay button — play/pause lives only in the bottom bar

---

## Syllable Grid — The Core Rule

Each lyric unit is a **generated line paired with its original below it**, aligned syllable-by-syllable in a shared CSS grid.

**Row splitting:** If a line has more syllables than fit on one screen row, it splits into multiple sub-rows. The split happens at syllable-column boundaries — both generated and original split at exactly the same position, so alignment is never lost. Max syllables per visual row is calculated from container width (≈ `containerWidth / 90px`, minimum 4). Each sub-row is its own grid:

```css
grid-template-columns: repeat(N, 1fr)  /* N = syllables in this sub-row */
```

Each word spans `word.length` grid columns (`grid-column: span N`). Generated row sits directly above its paired original row within the same sub-row grid. Both rows share the column template — syllables align vertically.

```
col:   1       2       3       4       5
gen:  [Fix   ][the   ][shelf ][right ][now   ]
orig: [Is    ][this  ][the   ][real  ][life  ]

col:   1──────2       3
gen:  [tight·en      ][the   ]    ← tight·en spans 2 cols
orig: [is    ][this  ][the   ]
```

**Wrap rule:** If the grid is too wide for the screen, both rows split at the same syllable-column boundary. Both rows always wrap together.

✅ CORRECT:
```
[Fix   ][the   ][shelf ]     ← generated cols 1–3
[Is    ][this  ][the   ]     ← original  cols 1–3

[right ][now   ]             ← generated cols 4–5
[real  ][life  ]             ← original  cols 4–5
```

❌ WRONG — rows wrap at different points, syllable alignment is lost.

---

## Accessibility

- All tap targets: minimum 48×48px
- Minimum contrast: 4.5:1 on all text
- Every affordance pairs color with shape or icon
- Minimum font size: 13px
- Progress bar: `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`

---

## v2 Screen Additions

When phones join in v2, the following screens are added:

| Screen | Purpose |
|---|---|
| Landing | Create room / join with code |
| Room (between rounds) | Vote feed — songs and datasets as carousels, sorted by votes |
| Voting Round | TV: live leaderboard + countdown; Phone: carousels + draining progress bar |
| Recap | Post-song summary; host triggers next round |

The Generating and Karaoke screens carry forward from v1. The Picker is replaced by the Room screen's vote feed in v2.
