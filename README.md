# AI Karaoke

**Docs-only repository.** Product and engineering specs live under [`docs/`](docs/). The Next.js app has been removed; scaffold the app when you are ready.

## What this is

Party karaoke where Claude rewrites lyrics syllable-for-syllable using an absurd text source (IKEA manuals, Yelp reviews, etc.). v1 scope: **one device** in the room (laptop or TV) — no rooms, voting, or guest phones.

## Documentation (source of truth)

| Doc | Purpose |
|-----|---------|
| [`docs/CHARTER.md`](docs/CHARTER.md) | Goals and version roadmap |
| [`docs/SRS.md`](docs/SRS.md) | Requirements by version |
| [`docs/SDD.md`](docs/SDD.md) | Architecture and data design |
| [`docs/API.md`](docs/API.md) | `/api/generate` contract and prompts |
| [`docs/UX.md`](docs/UX.md) | Screens and syllable grid |

## Seed data (optional)

Static catalog under `data/` (songs, datasets, LRC JSON) — not application code. Use when you scaffold the app.

## Next step

When ready: create a Next.js App Router project, implement per `docs/SDD.md` and `docs/API.md`, and wire UI per `docs/UX.md`. See [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md) for agent/human workflow.
