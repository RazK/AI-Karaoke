#!/usr/bin/env bash
# Build the handover archive.
#
#   tools/archive.sh            -> dist/ai-karaoke.tar.gz
#
# Contains the core, the app, the setup, the nine generated songs, the demo
# video and one page in my own words. Extracted onto a clean machine and handed
# to an agent with "set this up and run the demo", it comes up working.
#
# It does not contain any audio or any song's original lyric. setup.sh fetches
# the freely licensed songs itself, and anything copyrighted is fetched from the
# URL it came from, on the machine that runs it.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=dist
STAGE=$OUT/ai-karaoke
rm -rf "$STAGE"; mkdir -p "$STAGE"

echo "== code, app, setup"
for p in hollow app sing tools tests data docs README.md AGENTS.md setup.sh \
         requirements.txt .env.example .gitignore; do
  cp -r "$p" "$STAGE/"
done
find "$STAGE" -name __pycache__ -type d -prune -exec rm -rf {} +

echo "== the nine"
if [ -d out/nine ]; then
  mkdir -p "$STAGE/nine" && cp out/nine/* "$STAGE/nine/"
else
  echo "   (none yet — run tools/handover.py first)" >&2
fi

echo "== the demo video and the sung examples"
mkdir -p "$STAGE/demo"
[ -f out/demo/demo.mp4 ] && cp out/demo/demo.mp4 "$STAGE/demo/"
[ -f out/sing/original.mp3 ] && cp out/sing/original.mp3 out/sing/dressed.mp3 "$STAGE/demo/"
[ -f out/sing/README.md ] && cp out/sing/README.md "$STAGE/demo/sung-examples.md"

cat > "$STAGE/START-HERE.md" <<'EOF'
# Set this up and run the demo

```bash
./setup.sh --full
.venv/bin/python app/server.py     # then open http://localhost:8000
```

`setup.sh` installs ffmpeg, espeak-ng, CPU torch, a source separator (Demucs)
and a local speech model (Whisper), then seeds songs and runs the test suite.
It takes a while on a first run and downloads model weights. That is expected.

An Anthropic API key goes in `.env.local`. It is only needed for the inventive
end of the licence dial; everything else, including licence 0, works without one.

In this archive:

- `README.md` — what the system is and how the three parts work
- `docs/one-page.md` — what I changed my mind about, which of the nine I would
  show and which I would not, and where I think it breaks next
- `docs/prior-art.md` — whether this format was worth inventing (partly not)
- `nine/` — nine songs as plain text: every rewritten line with the original
  beside it, and the setting each was generated at. `nine/INDEX.md` compares them
- `demo/demo.mp4` — the system being used end to end, with sound
- `demo/original.mp3`, `demo/dressed.mp3` — a synthetic voice singing a song and
  then singing an IKEA manual, both from the representation alone
- `AGENTS.md` — the working rules, including the one that is not negotiable
EOF

mkdir -p "$OUT"
tar -czf "$OUT/ai-karaoke.tar.gz" -C "$OUT" ai-karaoke
rm -rf "$STAGE"
echo
echo "wrote $OUT/ai-karaoke.tar.gz  ($(du -h "$OUT/ai-karaoke.tar.gz" | cut -f1))"
