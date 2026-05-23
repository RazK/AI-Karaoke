# AI Karaoke — Cursor agent guide

Human-in-the-loop development: you assist with focused, reviewable work; the user directs scope, commits, and PRs.

## Before coding

1. Read **`docs/`** — especially `SDD.md`, `API.md`, `UX.md`
2. Read **`.cursor/rules/ai-karaoke-context.mdc`** — v1 scope and repo layout
3. Inspect **`data/`** — songs, datasets, LRC files to wire into the app

## v1 scope (locked)

- **One device** (laptop or TV): picker → generating → karaoke
- YouTube IFrame API for audio; AI lyric rewrite via `/api/generate`
- `localStorage` cache: `lyrics_<songId>_<datasetId>`
- **Out of scope unless the user asks:** rooms, guest phones, Supabase, voting (see `docs/SRS.md` for future requirements)

## Working rules

1. **Human-in-the-loop** — no unattended overnight runs, status churn, or coordination commits; no `logs/` in the repo
2. **One branch at a time** — small diffs; open a PR when the user asks
3. **Docs ↔ code before commit** — see `.cursor/rules/docs-consistency.mdc`. Every behavior/API/UX/architecture change updates the matching `docs/` file in the same commit; no duplication of what code already says clearly
4. **Commit only when the user asks** — never commit `.env` or `.env.local`
5. **Minimize scope** — match the request; scaffold the Next.js app only when asked
6. **Do not add** `logs/`, `scripts/output/`, or `__pycache__/`

## Next.js

When upgrading or scaffolding, check `node_modules/next/dist/docs/` for breaking changes in the installed version.

## Scaffolding the app

Follow `docs/SDD.md`, `docs/API.md`, and `docs/UX.md`. Build order: scaffold → `/api/generate` → screens → YouTube sync → deploy on Vercel.
