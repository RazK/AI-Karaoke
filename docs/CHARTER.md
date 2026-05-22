# AI Karaoke — Project Charter

## Project Summary

| Field | Value |
|---|---|
| Project | AI Karaoke |
| Owner | Raz Yosigal |
| Type | Hobby / personal project |
| Hard deadline | Party event (~2 weeks from project start) |
| Version | 1.0 |

## Vision

Party karaoke where an AI rewrites the lyrics. Groups pick a song and a ridiculous text source, watch Claude rewrite every line syllable-for-syllable, then try to sing the result to the original melody. Every session is unique. Every song is a disaster. **"The funniest thing you can do with a browser."**

## Goals

1. A working, usable app at a party of 6–15 people within 2 weeks
2. Full voting + karaoke loop end-to-end: join → vote → generate → sing
3. Zero friction to join — scan a QR code, no name, no account, no install

## Stakeholders

| Role | Person |
|---|---|
| Developer, product owner, primary user | Raz Yosigal |

## Success Criteria

The app succeeds at the party if a group of 6–15 people can:

1. Join a room by scanning a QR code with no friction
2. Vote for a song and dataset from their phones
3. Watch AI-generated lyrics appear on the host screen
4. Sing along — and find it funny

## Target Users

- **Primary:** Friend groups (4–15 people) in the same physical space — house parties, game nights, birthday parties. One laptop or TV, everyone else on their phone.
- **Not in v1:** Remote groups, solo users, large venues.

## Out of Scope (v1)

- Monetization or paid tiers
- Analytics, observability, or logging dashboards
- Room cleanup or lifecycle management
- Audio playback — groups play music on Spotify/YouTube on a separate device
- Word-level lyric highlight (full-line highlight only)
- Custom dataset upload
- User accounts or session history
- Native iOS/Android apps
- Localization or non-English songs

## Open Questions

| Question | Impact |
|---|---|
| Music playback: should groups play on a separate device, or should the app embed a YouTube player? | UX flow vs. licensing/ToS complexity |
| Song licensing: is displaying lyrics from well-known songs legally safe for personal party use? | Catalog scope |
