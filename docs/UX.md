# AI Karaoke — UX Design Brief

## Design System

### Colors (Kahoot-inspired)

| Token | Value | Usage |
|---|---|---|
| `bg-base` | `#19191C` | Page background |
| `bg-card` | `#2B2B35` | Cards, panels |
| `accent-purple` | `#864CBF` | Primary CTA buttons, active states |
| `accent-blue` | `#1368CE` | Song cards |
| `accent-orange` | `#E85C0D` | Dataset cards |
| `accent-yellow` | `#FFD600` | Active karaoke line highlight |
| `text-primary` | `#FFFFFF` | Generated lyrics, headings |
| `text-secondary` | `#A8A8B3` | Original lyrics, labels |
| `text-muted` | `#55555F` | Dim / previous lines |
| `success` | `#26890C` | Generation complete |

### Typography

Use a bold, rounded sans-serif: **Nunito**, **Poppins**, or **Rubik**.

| Element | Desktop | Mobile | Weight | Color |
|---|---|---|---|---|
| Generated lyric (current) | 52px | 26px | 800 | white |
| Original lyric (current) | 22px | 13px | 400 | `text-secondary` |
| Generated lyric (next/prev) | 36px | 20px | 700 | `text-muted` |
| Original lyric (next/prev) | 16px | 11px | 400 | `text-muted` |
| Card title | 20px | 18px | 700 | white |
| UI labels / buttons | 18px | 16px | 700 | white |

### Motion

| Element | Behavior |
|---|---|
| Line transitions | Smooth upward scroll, 300ms ease-out |
| Progress bar fill | `transition: width 100ms linear` |
| Screen transitions | Cross-fade 200ms |
| Card selection | Scale to 1.03 + accent border, 100ms |

### Layout Rules

- `height: 100svh` on all full-screen pages
- `overflow-x: hidden` on root — all content contained within 100vw
- Minimum tap target: 48×48px on all interactive elements
- Minimum font size: 13px

---

## Screens (v1)

v1 has three screens: **Picker → Generating → Karaoke**

---

### Screen 1 — Picker

**Purpose:** Host selects a song and a dataset, then generates.

```
┌──────────────────────────────────────────────────────────┐
│  AI Karaoke                                              │
│  "The AI rewrote your songs. You still have to sing them."│
├──────────────────────────────────────────────────────────┤
│                                                          │
│  🎵 Pick a Song          🔍 [search songs...   ]        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Bohemian     │  │ Never Gonna  │  │ Africa       │   │
│  │ Rhapsody     │  │ Give You Up  │  │              │   │
│  │ Queen · 5:54 │  │ Rick · 3:33  │  │ Toto · 4:55  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  📋 Pick a Dataset       🔍 [search datasets...]        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Yelp Reviews │  │ IKEA Manuals │  │ Horoscopes   │   │
│  │ (1-star)     │  │              │  │              │   │
│  │ Angry guests │  │ Assembly ins │  │ Vague cosmic │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│              [ Generate ← accent-purple, full-width ]    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Layout:**
- Two sections stacked vertically: Songs on top, Datasets below
- Each section: search bar + horizontally scrollable card row
- Cards: fixed width (~180px desktop, ~140px mobile), rounded, `bg-card`
- **Selected state:** accent-colored border (blue for songs, orange for datasets) + subtle scale-up
- One song and one dataset selected at a time

**Generate button:**
- Full-width, accent-purple
- Disabled until both a song and dataset are selected
- When active, shows the combo: *"Generate: Bohemian Rhapsody × IKEA Manuals"*

**Search:** Filters cards in real time as the host types. Shows *"No matches"* if nothing found.

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
│  🎵 Bohemian Rhapsody × 📋 IKEA Manuals   [Regenerate] [New]    │  ← top bar
├──────────────────────────────────────────────────────────────────┤
│                                            [YouTube ~200×120px]  │
│                                                                  │
│  ── previous line (20% opacity) ──────────────────────────────  │
│  [prev generated…]                                               │
│  [prev original…]                                                │
│                                                                  │
│  ══ CURRENT LINE ════════════════════════════════════════════    │
│  Fix     the     shelf    right    now                           │  52px bold white
│  Is      this    the      real     life                          │  22px gray
│  ▓▓▓▓▓▓▓▓▓▓▓▓ accent-yellow background bar ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │
│                                                                  │
│  ── next line (40% opacity) ───────────────────────────────── ─ │
│  [next generated…]                                               │
│  [next original…]                                                │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░   2:14 / 5:54           │  ← progress bar
└──────────────────────────────────────────────────────────────────┘
```

**Top bar (fixed):**
- Left: song × dataset label with emoji icons
- Right: **Regenerate** (ghost, small) + **New Combo** (ghost, small)

**YouTube player:**
- Always visible per YouTube ToS
- Positioned top-right, ~200×120px, clear of the lyric display

**Before Play:**
- YouTube player is loaded but paused
- Large **▶ Play** button overlays the lyric area
- Tapping Play calls `player.playVideo()` and starts the RAF timing loop simultaneously

**Line display:**
- 3 lyric units: previous (20% opacity), current (full + yellow bar), next (40% opacity)
- Lines slide upward smoothly, 300ms ease-out
- Font readable from 3 meters: 52px generated, 22px original on desktop

**Progress bar (fixed bottom):**
- Full-width, 8px height, `accent-yellow` fill
- Driven by `player.getCurrentTime()` every 100ms
- Time label right-aligned: `2:14 / 5:54`

---

## Syllable Grid — The Core Rule

Each lyric unit is a **generated line paired with its original below it**, aligned syllable-by-syllable in a shared CSS grid.

```css
grid-template-columns: repeat(N, 1fr)  /* N = total syllable count */
```

Each word's `grid-column` is `startSyllable / span syllableCount`. Both rows share the grid — syllables align vertically.

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
