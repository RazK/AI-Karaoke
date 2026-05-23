# AI Karaoke

Party karaoke on **one device** (laptop or TV): pick a song and an absurd text source, AI rewrites the lyrics **syllable-for-syllable**, and everyone sings along to YouTube audio with synced on-screen lyrics.

## What's in this repo

| Path | Contents |
|------|----------|
| [`docs/`](docs/) | v1 product and engineering specs — architecture, API, UX, requirements, charter |
| [`data/`](data/) | Seed catalog — songs, datasets, corpus text, LRC timing JSON |

The app is **not scaffolded yet**. Implementation follows the specs below.

## v1 intent

- **Single device** in the room — no guest phones, rooms, or voting in v1
- **Core loop:** picker → generating (AI lyrics) → karaoke (YouTube + syllable grid)
- **Cache:** generated lyrics in `localStorage` (`lyrics_<songId>_<datasetId>`)
- **Future:** multi-device party features are outlined briefly in [`docs/SRS.md`](docs/SRS.md)

## Start here

Read before writing code:

1. [`docs/SDD.md`](docs/SDD.md) — architecture, data model, deployment
2. [`docs/UX.md`](docs/UX.md) — screens, layout, syllable grid, YouTube sync
3. [`docs/API.md`](docs/API.md) — `/api/generate` contract and prompts

Supporting context: [`docs/SRS.md`](docs/SRS.md), [`docs/CHARTER.md`](docs/CHARTER.md). Doc index: [`docs/README.md`](docs/README.md).

**Cursor / agents:** [`AGENTS.md`](AGENTS.md) and [`.cursor/rules/ai-karaoke-context.mdc`](.cursor/rules/ai-karaoke-context.mdc).

## Build order

1. **Scaffold** — Next.js App Router on Vercel, Tailwind, catalog wired from `data/`
2. **`/api/generate`** — server route per `docs/API.md` (`ANTHROPIC_API_KEY` server-only)
3. **Screens** — picker, generating, karaoke per `docs/UX.md`
4. **YouTube sync** — IFrame API, LRC timing, syllable highlight, `localStorage` cache
5. **Deploy** — Vercel; preview URLs on PRs (see `docs/SDD.md`)

## Local setup

*After the Next.js app is scaffolded:*

```bash
npm install
```

Create `.env.local` with your Anthropic API key (server-side only — never exposed to the client):

```bash
ANTHROPIC_API_KEY=
```

Run the dev server and implement screens per `docs/UX.md`. Deploy target: **Vercel**.
