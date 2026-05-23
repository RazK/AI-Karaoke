# AI Karaoke — Claude Context

**Docs-only repo.** Syllable-matched lyric rewrite for **one laptop or TV** (v1). Read `docs/SDD.md`, `docs/API.md`, and `docs/UX.md` before coding. Scope: `docs/SRS.md`; goals: `docs/CHARTER.md`.

## v1 product (locked)

- Single device in the room — **no** rooms, phones-as-guests, Supabase, or voting.
- Intended flow: picker → generating → karaoke; absurd lyrics from Claude; YouTube for audio.
- **App not started** — specs and seed `data/` only until you scaffold.

## Architecture (when you build)

| Piece | Choice |
|-------|--------|
| Frontend | Next.js App Router on Vercel |
| Generate | One serverless route: `app/api/generate/route.ts` (Claude; `ANTHROPIC_API_KEY` server-only) |
| Audio | YouTube IFrame API (`youtubeId` in `data/songs.json`) |
| Timing | Line LRC in `data/lrc/*.json`; word-level `*-words.json` when added |
| State | React state + `localStorage` cache (`lyrics_<songId>_<datasetId>`) |
| Catalog | `data/songs.json`, `data/datasets.json`, `data/lrc/` |

**Specs:** `docs/` is the only product/engineering spec.

## Next step

Scaffold Next.js per `docs/SDD.md`, then implement `/api/generate` per `docs/API.md` and screens per `docs/UX.md`. See `AGENTS.md` for human-in-the-loop rules.

## v2 (reference only)

Multi-device party mode: rooms, Supabase, voting. See `docs/SRS.md` and `docs/archive/` if present. Do not plan v2 as part of v1 scaffold unless the user asks.
