#!/usr/bin/env bash
# Set this up on a clean machine and run the demo.
#
#   ./setup.sh          install everything and seed one song
#   ./setup.sh --full   also seed the three songs the nine deliverables use
#
# This is allowed to be slow. It installs a source separator and a speech model
# and downloads their weights the first time they run. A first ingest takes a
# few minutes; the app says what it is doing while it waits.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

say "System packages"
if command -v apt-get >/dev/null; then
  sudo=""; [ "$(id -u)" -ne 0 ] && sudo="sudo"
  $sudo apt-get update -qq
  $sudo apt-get install -y -qq ffmpeg espeak-ng
elif command -v brew >/dev/null; then
  brew install ffmpeg espeak-ng
else
  echo "Install ffmpeg and espeak-ng by hand, then run this again." >&2; exit 1
fi

say "Python environment"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
# CPU torch first, so a machine without a GPU does not pull gigabytes of CUDA.
.venv/bin/pip install -q --index-url https://download.pytorch.org/whl/cpu torch torchaudio
.venv/bin/pip install -q -r requirements.txt

say "API key"
if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "Wrote .env.local. Put an Anthropic key in it to use the inventive end of"
  echo "the licence dial. Everything else, including licence 0, works without one."
fi

say "Seeding a song"
# Through the ordinary karaoke-file path, not a special one: JamendoLyrics is
# freely licensed and comes with hand-checked word timings, so it is also what
# the calibration and the tests run against.
.venv/bin/python tools/jamendo.py Avercage_-_Embers
if [ "${1:-}" = "--full" ]; then
  .venv/bin/python tools/jamendo.py Cortez_-_Feel__Stripped_ Wordsmith_-_The_Statement
  .venv/bin/python tools/youtube.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
fi

say "Checking the exam is calibrated"
.venv/bin/python -m pytest tests/ -q

cat <<'EOF'

Ready.

  .venv/bin/python app/server.py     then open http://localhost:8000

Add a song from a YouTube URL or import a karaoke file with its recording,
pick or paste a body of text, set the licence dial, and play it.
EOF
