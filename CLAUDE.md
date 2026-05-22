@AGENTS.md

# AI Karaoke — Claude Context

Party karaoke app. Read `docs/SDD.md` for architecture, `docs/API.md` for endpoints, `docs/UX.md` for screens. `docs/SRS.md` is scope; `docs/CHARTER.md` is goals.

## v1 Architecture (locked — do not re-discuss)

- **Frontend:** Next.js (App Router) on Vercel
- **Backend:** Single Vercel serverless function at `app/api/generate/route.ts` — Claude API proxy; key stays server-side
- **Audio:** YouTube IFrame API — embedded on the karaoke screen; each song has a `youtubeId` in `songs.json`
- **Timing:** `player.getCurrentTime() * 1000` in a RAF loop — frame-accurate sync to audio playback
- **State:** React state only — no database, no real-time
- **Cache:** Generated lyrics stored in localStorage under `lyrics_<songId>_<datasetId>`
- **Catalog:** Static JSON files (`data/songs.json`, `data/datasets.json`, `data/lrc/*.json`)
- **Word-level highlight:** v1 highlights the full active line. Word-level is a future enhancement.
- **Deployment:** Vercel auto-deploys `main`. PR preview URLs for testing.

## Branch state

| Branch | Status | Description |
|---|---|---|
| `main` | ✅ current | Docs only — app scaffold is next |

## Build phases (in order)

### Phase 1 — `feat/nextjs-scaffold`
Initialize Next.js App Router project. Install: `lrc-kit`, `tailwindcss`, `@anthropic-ai/sdk`. Build 3 screens per `docs/UX.md`: Picker, Generating, Karaoke.

### Phase 2 — `feat/generate-api`
Serverless function at `app/api/generate/route.ts`. Full spec in `docs/API.md`.

### Phase 3 — `feat/karaoke-sync`
YouTube IFrame integration + RAF timing loop. Spec in `docs/SDD.md § 4.3`.

## Environment variables

```
ANTHROPIC_API_KEY=    # Server-side only
```

## v2 additions (for reference)

When phones join: add Supabase (real-time + DB), room system, guest identity (UUID + optional nickname), voting, companion lyric view on phones. The `/api/generate` route carries forward unchanged. Full v2 spec in `docs/SRS.md § 3` and `docs/SDD.md § 6`.
