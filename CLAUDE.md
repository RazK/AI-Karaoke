@AGENTS.md

# AI Karaoke — Claude Context

Party karaoke web app. Read `docs/SDD.md` for architecture, `docs/API.md` for endpoints, `docs/UX.md` for screens. `docs/SRS.md` is scope; `docs/CHARTER.md` is goals.

## Architecture (locked — do not re-discuss)

- **Frontend:** Next.js (App Router) on Vercel
- **Real-time + DB:** Supabase — single managed service for real-time subscriptions and DB
- **AI:** Vercel serverless function at `app/api/generate/route.ts` — proxies Claude API; key stays server-side
- **Audio:** YouTube IFrame API — embedded on the host/TV karaoke screen; each song has a `youtubeId` in `songs.json`
- **Timing — host:** `player.getCurrentTime() * 1000` in a RAF loop → frame-accurate sync to audio
- **Timing — guests:** `Date.now() - songStartedAt` in a RAF loop → < 500ms drift, acceptable for reading lyrics
- **Host auth:** 4-digit PIN stored in `rooms.host_pin`; sent in request body for host-only actions
- **Guests:** Anonymous. UUID in `localStorage` is the only identity.
- **Voting:** Feed-based upvote (search → propose → upvote). Host starts a 30s timed round. Winning combo = top-voted song × top-voted dataset independently.
- **Word-level highlight:** v1 highlights the full active line. Word-level is a future enhancement.
- **Deployment:** Vercel auto-deploys `main`. PR preview URLs for testing.

## Branch state

| Branch | Status | Description |
|---|---|---|
| `main` | ✅ current | Docs only — app scaffold is next |

## Build phases (in order)

### Phase 1 — `feat/supabase-schema`
SQL migrations for the 4 tables in `docs/SDD.md § 3.1`. Enable Realtime on `rooms`, `votes_songs`, `votes_datasets`. Apply RLS policies.

### Phase 2 — `feat/nextjs-scaffold`
Initialize Next.js App Router project. Install: `@supabase/supabase-js`, `@supabase/ssr`, `lrc-kit`, `tailwindcss`, `@anthropic-ai/sdk`. Build all 6 screens per `docs/UX.md`.

### Phase 3 — `feat/generate-api`
Serverless function at `app/api/generate/route.ts`. Full spec in `docs/API.md` (Generate endpoint + Claude Prompt Strategy).

### Phase 4 — `feat/karaoke-sync`
YouTube IFrame integration + RAF timing loop. Host screen uses `player.getCurrentTime()`; guest screens use `songStartedAt` timestamp. Full spec in `docs/SDD.md § 4.4`.

## Environment variables

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
ANTHROPIC_API_KEY=
```

## Supabase client helpers (to create in Phase 2)

```
utils/supabase/client.ts     — browser client (createBrowserClient)
utils/supabase/server.ts     — server component client (createServerClient)
utils/supabase/middleware.ts — middleware session refresh
```
