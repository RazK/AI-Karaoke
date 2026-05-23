# UI V1 — Draft Implementation

This folder contains the first-pass UI built during scaffolding.

**Status:** Draft. Owner is not satisfied with it. Do not invest further in these files.

**The authoritative UX spec is `docs/UX.md`.** That document describes what any UI implementation should do. This folder is one attempt — not the final one.

## What is here

| File | What it does |
|------|-------------|
| `PickerScreen.tsx` | Song + dataset picker, generate button |
| `GeneratingScreen.tsx` | Progress screen while API runs (uses mock data) |
| `KaraokeScreen.tsx` | Scrollable lyrics view with word highlight + seekbar |

## Known problems

- GeneratingScreen still uses mock data — real `/api/generate` not wired up
- KaraokeScreen timing is mock (3s per line) — not driven by YouTube
- Overall visual design is not satisfying — too much iteration without a clear design direction
- Word-level timing is approximated from syllable proportions, not real timestamps

## If you are building a new UI

Read `docs/UX.md` for the interaction spec.  
Read `docs/SDD.md` for data structures and timing architecture.  
Read `app/types.ts` for the TypeScript interfaces your components must accept.  

Do not copy from this folder as a starting point. Start fresh from the spec.
