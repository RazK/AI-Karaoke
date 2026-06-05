---
description: Generate lyrics for a Jamendo song via the web app. Use when the user wants to generate a new song+corpus combo.
allowed-tools: Bash
---

The web app at http://localhost:8000 is the primary interface for generating lyrics.

To generate programmatically (e.g. for testing), POST to the API directly:

```bash
curl -s -X POST http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"song_id": "$SONG_ID", "corpus": "$CORPUS_ID"}' | jq .
```

To list available songs and corpora:
```bash
curl -s http://localhost:8000/api/songs | jq '[.[] | {id, artist, title}]'
curl -s http://localhost:8000/api/corpora | jq .
```

Make sure `server.py` is running (`python server.py`) before calling these.
