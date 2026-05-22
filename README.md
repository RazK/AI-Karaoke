# AI Karaoke

*"The AI rewrote your songs. You still have to sing them."*

Party karaoke where Claude rewrites every lyric line syllable-for-syllable using an absurd text source — IKEA manuals, Yelp reviews, legal disclaimers. The melody stays. The words become chaos.

## How it works

1. Pick a song and a ridiculous dataset
2. Claude rewrites every line, syllable-for-syllable
3. Music plays inside the app; lyrics scroll in sync
4. Sing. Chaos ensues.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router), Tailwind CSS |
| AI | Claude API (`claude-sonnet-4`) via Vercel serverless |
| Audio | YouTube IFrame API |
| Lyric timing | LRCLib + `lrc-kit` |
| Hosting | Vercel |

## Setup

> Setup instructions will be added once the Next.js project is initialized.

Environment variables (`.env.local`):
```
ANTHROPIC_API_KEY=
```

## Documentation

| Doc | Contents |
|---|---|
| [`docs/CHARTER.md`](docs/CHARTER.md) | Project goals, versions (v1/v2/v3), success criteria |
| [`docs/SRS.md`](docs/SRS.md) | All functional and non-functional requirements by version |
| [`docs/SDD.md`](docs/SDD.md) | System architecture, data design, component design |
| [`docs/API.md`](docs/API.md) | API routes and Claude prompt strategy |
| [`docs/UX.md`](docs/UX.md) | Design system, all screens, syllable grid spec |
| [`CLAUDE.md`](CLAUDE.md) | AI agent working context and build phases |
