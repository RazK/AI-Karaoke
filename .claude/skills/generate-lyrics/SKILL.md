---
description: Generate new lyrics for a song by fitting words from a corpus onto its lyric structure. Use when the user provides a song title and a corpus name and wants new lyrics generated.
allowed-tools: Bash
---

Run the lyric generation script:

```bash
ANTHROPIC_API_KEY=$(cat .env.local | cut -d= -f2) \
.venv/bin/python lyric_engine.py $ARGUMENTS
```

`$ARGUMENTS` should be: `"<title>" <corpus-name> [artist]`

Examples:
- `/generate-lyrics "A Whole New World" ikea-manuals`
- `/generate-lyrics "Imagine" ikea-manuals "John Lennon"`  ← only if multiple artists share the title

The song's lyric structure (syllable count + stress pattern + rhyme scheme) is derived from
the original lyrics using the CMU pronouncing dictionary.
If multiple artists share the title, the script will list them and ask the user to re-run with the artist specified.
The corpus is loaded from `data/datasets/<corpus-name>.txt`.

Show the output exactly as printed.
