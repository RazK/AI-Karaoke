# AI Karaoke — UX Design Brief

Build v1 UI from this doc and [`docs/inspiration/moodboard.html`](inspiration/moodboard.html). Functional requirements: [`docs/SRS.md`](SRS.md) §2.

---

## Product feel

Party karaoke on a laptop/TV: pick song + absurd corpus → AI rewrites lyrics → everyone sings along.

The UI feels like a **small party game**: warm stage, big readable type, dry humor — readable from the couch.

**Tagline (picker):** *The AI rewrote your songs. You still have to sing them.*

**Avoid:** SaaS dashboards, glass blur, gradient CTAs, hacker-terminal chrome, mascot clutter, dual scoreboards, particle effects.

---

## Visual references

Gallery: [`docs/inspiration/moodboard.html`](inspiration/moodboard.html)

| Asset | Use for |
|---|---|
| `mock-b-refined-v2-trio.png` | **Primary layout** — all three screens (picker, generating, karaoke) |
| `01-jackbox-quiplash.png`, `02-jackbox-gameplay-tv.png` | Party-game typography and TV pacing |
| `03-mschf-catalog.png` | Dry humor in labels; optional monospace catalog rows |
| `mock-c-refined-trio.png` | Flavor text and status-line tone (sparingly) |
| `mock-classic-karaoke.png` | Syllable highlight fallback (green done / red now / white next) |

Mocks are **layout and tone targets**, not pixel-perfect spec.

---

## Design principles

1. **Party game, not app.** Deep purple stage, rounded cream cards, carousel pickers, hot-pink CTA, yellow lyric highlight.
2. **Less clutter.** One accent family. No badges, glow stacks, or decorative chrome.
3. **Funny, not edgy.** Generating copy sounds like a game-show host — light, dumb, dataset-themed.
4. **Lyrics are the hero.** Karaoke screen is mostly type; controls stay thin.
5. **One system.** Monospace is optional for status lines or list indices — not the whole UI.

---

## Visual language

| Element | Direction |
|---|---|
| Background | Deep purple / navy stage |
| Picker cards | Rounded cream/white; carousel with arrows + dot indicators |
| CTA | Hot pink pill — `LET'S GO · {song} × {dataset}` |
| Headers | Bold rounded display sans |
| Body / lyrics | Clean sans; karaoke active line very large |
| Accents | Pink buttons and progress; yellow active word |
| Motion | Screen cross-fade; progress fill; flavor text rotates ~2.5s |

Match the primary mock unless contrast fails accessibility targets below.

---

## Screens (v1)

**Picker → Generating → Karaoke**

### Screen 1 — Picker

Host picks song + dataset, then generates.

- Header: product name + tagline
- Two carousel cards side by side: **Choose a Song** | **Choose a Dataset**
- Each card: title, subtitle, prev/next arrows, dot indicators
- Optional search/filter per column
- Bottom CTA full width; disabled until both selected; label shows combo or what's missing
- Selected state: clear border or fill — no scale or glow halos

### Screen 2 — Generating

~7–10s wait during Claude API call.

- Stage background; simple marquee frame (subtle bulb line OK)
- Large centered combo: `{song} × {dataset}`
- Progress bar + percent
- One rotating flavor line (dataset-themed jokes welcome)

Examples: *"Counting syllables…"*, *"Consulting the allen key…"*, *"Cross-referencing the reviews…"*

On error: *"That didn't work — tap to try again."* Return to picker with selections kept.

### Screen 3 — Karaoke

YouTube audio + synced dual-line lyrics. Hero screen.

- Top bar: `{song} × {dataset}` · Regenerate · New Combo
- Center: scrollable lyrics; active line largest
- Generated row above original (syllable grid below)
- Active word: yellow flat highlight (underline or background)
- Past/next lines: lower opacity
- Auto-scroll to center active line; pause 3s after manual scroll
- Bottom: play/pause, seekbar, time, minimized YouTube iframe (~80×45px)
- Starts paused; ▶ starts player + timing loop together
- Word timing from `data/lrc/<id>-words.json` when present; else syllable-proportional within line

---

## Syllable grid

Each unit = **generated line above original**, syllable-aligned in shared CSS grid.

```css
grid-template-columns: repeat(N, 1fr)  /* N = syllables in sub-row */
```

Each word spans `word.length` columns. On overflow, **both rows split at the same syllable boundary** (min ~4 syllables per sub-row, ~90px per column).

```
gen:  [Fix   ][the   ][shelf ][right ][now   ]
orig: [Is    ][this  ][the   ][real  ][life  ]
```

---

## Accessibility

- Tap targets ≥ 48×48px
- Body text contrast ≥ 4.5:1
- Selection not by color alone (border, weight, or marker)
- Progress: `role="progressbar"` + `aria-valuenow`
- Karaoke active line may exceed 13px for distance reading

---

## v2 (out of scope)

Landing, Room vote feed, Voting Round, Recap — [`docs/SRS.md`](SRS.md) §3. Generating + Karaoke carry forward.

---

## Implementer checklist

- [ ] Read this file + `docs/inspiration/moodboard.html`
- [ ] Three screens match primary mock structure
- [ ] Syllable grid wraps correctly (generated + original same break points)
- [ ] Flow matches [`docs/SDD.md`](SDD.md) §4.1
- [ ] PR includes screenshots of all three screens
