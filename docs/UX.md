# AI Karaoke — UX Design Brief

## Visual direction (in progress)

**Pick one direction before scaffold** — not a hybrid. Assets and mocks: [`docs/inspiration/moodboard.html`](inspiration/moodboard.html).

| Candidate | Leading mock | Spirit |
|---|---|---|
| **B — Party game** | `mock-b-refined-v2-trio.png` | Jackbox/showtime: carousel cards, stage, marquee, big lyrics |
| **C — Terminal catalog** | `mock-c-refined-trio.png` | Friendly monospace catalog, dry jokes, readable karaoke |

Shared principles (both directions):

1. **Less clutter.** No mascots, scoreboards, badge stickers, or glow stacks.
2. **Funny, not edgy.** Game-show host energy — never creepy or menacing.
3. **Readable from the couch.** Karaoke screen is mostly lyrics; chrome stays thin.

Rejected: old glass/violet SaaS spec; B v1 “refined” that looked like terminal UI (`mock-b-refined-trio.png`).

Screen flow and syllable grid below apply regardless of which visual direction wins.

---

## Screens (v1)

**Picker → Generating → Karaoke**

---

### Screen 1 — Picker

**Purpose:** Host picks song + dataset, then generates.

```
┌────────────────────────────────────────────────────────────────────────┐
│  AI KARAOKE                                                            │
│  The AI rewrote your songs. You still have to sing them.               │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   SONGS                              DATASETS                          │
│   [search…]                          [search…]                         │
│                                                                        │
│   #1  Bohemian Rhapsody              #1  Yelp Reviews (1-star)           │
│       Queen · 5:54                       Furious customer complaints     │
│   #2  Never Gonna Give You Up  ←       #2  IKEA Manuals            ←     │
│       Rick Astley · 3:33                 Step-by-step assembly…          │
│   #3  Africa                         #3  Legal Disclaimers              │
│       Toto · 4:55                        Terms of service boilerplate    │
│   …                                  …                                   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │  GENERATE · Never Gonna Give You Up × IKEA Manuals             │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

**Layout:**
- Two equal columns: **Songs** | **Datasets** (landscape laptop/TV)
- Each column: header, search, scrollable list
- Rows read like a **catalog** (optional `#` index, monospace OK) — not illustrated cards
- **Selected row:** solid invert or single accent border/background — no scale, no glow halos

**Generate button:**
- Full width below columns, pinned bottom
- Disabled until both selected; label shows current combo or what's missing
- Active: solid fill (accent or white on black) — not a gradient pill

**Search:** Per-column filter; selection persists when filtered out of view.

---

### Screen 2 — Generating

**Purpose:** ~7–10s wait during Claude API call.

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│              Never Gonna Give You Up × IKEA Manuals                      │
│                         (large, centered)                              │
│                                                                        │
│              ████████████░░░░░░░░░░  ~60%                              │
│                                                                        │
│              "Counting syllables…"                                     │
│              (rotates every 2.5s — host jokes, dataset-themed)           │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

**Flavor text** — short, dumb, friendly (examples):
- *"Counting syllables…"*
- *"Consulting the manual…"*
- *"The AI is taking notes…"*
- *"Cross-referencing the reviews…"*

**Avoid:** menace, "do not make eye contact," fake file paths, fake warnings.

**Progress:** Simple bar 0→~90%, then 100% on success.

**On error:** *"That didn't work — tap to try again."* Return to Picker with selections kept.

---

### Screen 3 — Karaoke

**Purpose:** YouTube audio + synced dual-line lyrics. Hero screen.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Never Gonna Give You Up × IKEA Manuals          [Regenerate] [New]    │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│     (past lines — muted)                                               │
│                                                                        │
│  ═══════════════════════════════════════════════════════════════════   │
│     Fix    the   shelf    right   now          ← generated, large        │
│     Is     this  the      real    life         ← original, smaller       │
│            ░░ active word highlight ░░                                  │
│  ═══════════════════════════════════════════════════════════════════   │
│                                                                        │
│     (next lines — muted)                                               │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  [▶/❚❚]  ████████████░░░░░░░░  2:14 / 5:54              [YouTube mini] │
└────────────────────────────────────────────────────────────────────────┘
```

**Top bar:** Combo name + two text actions (Regenerate, New Combo). No emoji clutter unless one icon max.

**Lyrics:**
- Active line: largest type; optional thin accent bar at left (not full-width glow)
- Generated above original; syllable grid per rules below
- Past/next lines: lower opacity only — no extra effects
- Auto-scroll to center active line; pause 3s after manual scroll

**Word highlight:** One accent color on the active word (flat background or underline). Use `-words.json` timings when present; else syllable-proportional split.

**Bottom bar:** Play/pause, seekbar, time, minimized YouTube iframe (~80×45px).

**Playback:** Starts paused; ▶ starts player + timing loop together.

---

## Syllable Grid — The Core Rule

Each lyric unit is a **generated line paired with its original below it**, aligned syllable-by-syllable in a shared CSS grid.

**Row splitting:** If a line has more syllables than fit on one screen row, split at syllable-column boundaries — both rows split together. Max syllables per row ≈ `containerWidth / 90px`, minimum 4.

```css
grid-template-columns: repeat(N, 1fr)  /* N = syllables in this sub-row */
```

Each word spans `word.length` columns (`grid-column: span N`).

```
col:   1       2       3       4       5
gen:  [Fix   ][the   ][shelf ][right ][now   ]
orig: [Is    ][this  ][the   ][real  ][life  ]
```

**Wrap rule:** Both rows always wrap at the same syllable-column boundary.

✅ CORRECT — same split point on both rows.  
❌ WRONG — rows wrap at different points.

---

## Accessibility

- Tap targets: minimum 48×48px
- Contrast: 4.5:1 on body text
- Do not rely on color alone — selected row also changes weight or `>` marker
- Minimum font size: 13px (UI chrome); karaoke active line exempt for distance reading
- Progress bar: `role="progressbar"` + `aria-valuenow`

---

## v2 Screen Additions

When phones join in v2:

| Screen | Purpose |
|---|---|
| Landing | Create room / join with code |
| Room | Vote feed — songs and datasets as carousels |
| Voting Round | TV leaderboard + countdown; phones vote |
| Recap | Post-song summary |

Generating and Karaoke carry forward from v1. Picker is replaced by Room vote feed in v2.
