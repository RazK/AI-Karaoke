# AI Karaoke — Project Charter

## Project Summary

| Field | Value |
|---|---|
| Project | AI Karaoke |
| Owner | Raz Karl |
| Type | Hobby / personal project |
| Hard deadline | Party event (~2 weeks from project start) |

## Vision

*"The AI rewrote your songs. You still have to sing them."*

Party karaoke where Claude rewrites every lyric line syllable-for-syllable using an absurd text source — IKEA manuals, Yelp reviews, legal disclaimers. The melody stays. The words become chaos. A funny, special, memorable night in with your friends.

## Goals

1. Working app at a party within 2 weeks
2. Host picks a song + dataset, generates rewritten lyrics, and sings along — all from one device
3. The generated lyrics are actually singable (syllable-accurate) and actually funny

## Target Users

Friend groups (4–15 people) in the same physical space. One host laptop or TV. Everyone watches and sings together.

## Versions

### v1 — Single Device (current)
The host opens the app on a laptop or TV, picks a song and a dataset, generates AI-rewritten lyrics, and sings along. Pick → Generate → Sing.

### v2 — Phones Join
Guests join from their phones via QR code or room code. Optional nicknames. Live voting on song + dataset combos from the feed. Companion lyric view on phones.

### v3 — History + Ratings
Saved combo history per device. After each song, guests rate the combo 1–5 stars. Host browses a "Greatest Hits" catalog of past combos and can replay favorites.

### Later (not numbered)
Bring-your-own YouTube songs and custom text corpora — see `docs/SRS.md` §5. Potential backend/worker pipeline; independent of v2/v3 party features.

## v1 Success Criteria

A group of people can gather around a laptop, pick a song and a dataset, watch Claude generate the rewritten lyrics, and sing along to the music — and find it funny.

