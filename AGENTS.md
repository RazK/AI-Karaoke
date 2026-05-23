# AI Karaoke — Agent Guide (human-controlled)

This repo is maintained **with a human in the loop**. Agents assist; they do not run unattended overnight builds or parallel swarms.

## Current state

- **Docs only** — authoritative specs in `docs/`. No `app/`, no `package.json`, no `scripts/`.
- **Seed data** — `data/` holds catalog JSON/LRC for when the app is scaffolded.

## Source of truth

Read before coding:

| Doc | Purpose |
|-----|---------|
| `docs/SDD.md` | Architecture and data design |
| `docs/API.md` | `/api/generate` contract and prompts |
| `docs/UX.md` | Screens, layout, syllable grid |
| `docs/SRS.md` | Requirements by version |
| `docs/CHARTER.md` | Goals and version roadmap |

Party-room / Supabase / voting specs (if archived) live under `docs/archive/` — **v2 only**, not v1 work.

## Working rules

1. **No autonomous overnight sessions** — no `logs/`, no agent status commits, no pre-flight automation.
2. **One branch at a time** — small, reviewable changes; open a PR when the user asks.
3. **Commit only when the user asks** — never push secrets (`.env`, `.env.local`).
4. **Do not add** `logs/`, `scripts/output/`, or `__pycache__/` to the repo.
5. **Minimize scope** — docs and seed data unless the user expands scope to scaffold the app.

## When scaffolding the app

Follow `docs/SDD.md`, `docs/API.md`, and `docs/UX.md`. v1: single device, picker → generating → karaoke, YouTube IFrame API, `localStorage` cache for generated lyrics.
