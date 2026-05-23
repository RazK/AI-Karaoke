@AGENTS.md

# AI Karaoke — Claude Context

Party karaoke app. Read `docs/SDD.md` for architecture, `docs/API.md` for endpoints, `docs/UX.md` for screens. `docs/SRS.md` is scope; `docs/CHARTER.md` is goals.

**For multi-agent parallel work: read `AGENTS.md` — it has your branch, file ownership, and done criteria.**

---

## Architecture (locked)

- **Frontend:** Next.js (App Router) on Vercel
- **Backend:** Single Vercel serverless function at `app/api/generate/route.ts` — Claude API proxy; key stays server-side
- **Audio:** YouTube IFrame API — embedded on the karaoke screen; each song has a `youtubeId` in `songs.json`
- **Timing:** Per-word timestamps from `openai-whisper` alignment (`data/lrc/<songId>-words.json`)
- **State:** React state + localStorage
- **Cache:** Generated lyrics stored in localStorage under `lyrics_<songId>_<datasetId>`
- **Catalog:** Static JSON files (`data/songs.json`, `data/datasets.json`, `data/lrc/*.json`)
- **Deployment:** Vercel auto-deploys `main`. PR preview URLs for testing.

---

## Folder structure

```
/
├── app/
│   ├── api/generate/route.ts   ← THE API (Agent C builds this)
│   ├── ui/v1/                  ← Draft UI — frozen, not satisfying, will be replaced
│   │   └── README.md           ← Read this before touching anything in here
│   ├── components/             ← Minimal wiring only (routing glue)
│   ├── types.ts                ← Shared TypeScript interfaces — source of truth for data shapes
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── scripts/                    ← Python agents work here (generate.py, align.py)
├── data/
│   ├── songs.json
│   ├── datasets.json
│   └── lrc/                    ← Line-level LRC + word-level *-words.json (Agent B adds these)
└── docs/                       ← Authoritative specs — read before coding
    ├── UX.md                   ← What the UI must do (not how)
    ├── API.md                  ← /api/generate contract + prompt strategy
    ├── SDD.md                  ← System design
    └── SRS.md                  ← Full scope
```

---

## What is NOT done yet (as of project start)

- `app/api/` — does not exist. Agent C builds it.
- `scripts/` — does not exist. Agents A and B build it.
- `data/lrc/*-words.json` — does not exist. Agent B builds it.
- A satisfying UI — `app/ui/v1/` is a draft the owner is not happy with. Agent UI replaces it after the algorithm is proven.

---

## Environment variables

```
ANTHROPIC_API_KEY=    # Server-side only — never in client code
```

---

## v2 additions (reference only)

When phones join: add Supabase (real-time + DB), room system, guest identity (UUID + optional nickname), voting, companion lyric view on phones. The `/api/generate` route carries forward unchanged. Full v2 spec in `docs/SRS.md § 3` and `docs/SDD.md § 6`.
