# AI Karaoke

Party karaoke where an AI rewrites the lyrics. Pick a song, pick a dataset, watch Claude rewrite every line syllable-for-syllable, then try to sing it. Every session is unique. Every song is a disaster.

## How it works

1. Host opens the app on a laptop or TV — a room code + QR code appear
2. Guests scan with their phones — no account, no name, instantly in
3. Everyone votes for songs and datasets from a live feed on their phones
4. AI rewrites the lyrics syllable-for-syllable using the chosen dataset
5. Song plays inside the app; lyrics scroll karaoke-style in sync
6. Sing. Chaos ensues. Vote for the next round.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router), Tailwind CSS |
| Real-time + DB | Supabase |
| AI | Claude API (`claude-sonnet-4`) |
| Audio | YouTube IFrame API |
| Lyric timing | LRCLib + `lrc-kit` |
| Hosting | Vercel |

## Setup

> The app is not scaffolded yet — setup instructions will be added when the Next.js project is initialized.

You will need:
- A Supabase project (free tier) — copy the URL and anon key
- An Anthropic API key
- A Vercel account (free tier) for deployment

Environment variables (`.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
ANTHROPIC_API_KEY=
```

## Documentation

| Doc | Contents |
|---|---|
| [`docs/CHARTER.md`](docs/CHARTER.md) | Project goals, stakeholders, success criteria, out of scope |
| [`docs/SRS.md`](docs/SRS.md) | All functional and non-functional requirements; user stories |
| [`docs/SDD.md`](docs/SDD.md) | System architecture, data models, component design, deployment |
| [`docs/API.md`](docs/API.md) | REST endpoints, Supabase Realtime events, Claude prompt |
| [`docs/UX.md`](docs/UX.md) | Design system, all 6 screens, layout rules |
| [`CLAUDE.md`](CLAUDE.md) | AI agent working context — architecture decisions and build plan |
